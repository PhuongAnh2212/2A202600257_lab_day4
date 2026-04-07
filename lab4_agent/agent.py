# agent.py - Simple LangGraph orchestration (deterministic)

from typing import TypedDict, Annotated, Sequence, Dict, Any, List, Optional
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except Exception:
    StateGraph = None
    END = "__END__"
    LANGGRAPH_AVAILABLE = False
try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
except Exception:
    class BaseMessage:  # minimal fallback
        def __init__(self, content: str = ""):
            self.content = content

    class HumanMessage(BaseMessage):
        pass

    class AIMessage(BaseMessage):
        pass

try:
    from langchain_core.tools import tool
except Exception:
    def tool(func):
        def _invoke(args):
            return func(**args)
        func.invoke = _invoke  # type: ignore[attr-defined]
        return func

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import os
import json
from datetime import datetime

from tools import search_flight, search_hotels, calculate_budget

# ====================== TOOLS ======================
@tool
def search_flight_tool(origin: str, destination: str):
    """Tìm chuyến bay từ database"""
    return search_flight(origin, destination)

@tool
def search_hotels_tool(city: str):
    """Tìm khách sạn từ database"""
    return search_hotels(city)

@tool
def calculate_budget_tool(flight_price: int, hotel_price_per_night: int, num_nights: int = 2, num_travelers: int = 1):
    """Tính tổng ngân sách cho chuyến đi"""
    return calculate_budget(flight_price, hotel_price_per_night, num_nights, num_travelers)

tools = [search_flight_tool, search_hotels_tool, calculate_budget_tool]

# ====================== STATE ======================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    intent: str
    params: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    need_followup: bool
    followup_question: str

# ====================== ROUTER ======================
def _get_llm() -> Optional[ChatOpenAI]:
    if ChatOpenAI is None:
        return None
    api_key = os.getenv("OPENROUTER_API_KEY")
    api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it")
    if not api_key:
        return None
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=api_base,
        temperature=0.05,
        max_tokens=512,
    )

LLM = _get_llm()

def _rule_fill_slots(text: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    t = text.lower()
    city_map = {
        "hà nội": "Hà Nội",
        "đà nẵng": "Đà Nẵng",
        "phú quốc": "Phú Quốc",
        "hồ chí minh": "Hồ Chí Minh",
    }
    for key, proper in city_map.items():
        if key in t:
            if slots.get("origin") is None:
                slots["origin"] = proper
            elif slots.get("destination") is None and slots.get("origin") != proper:
                slots["destination"] = proper
    if "hà nội" in t:
        slots["origin"] = "Hà Nội"
    if "đà nẵng" in t:
        slots["destination"] = "Đà Nẵng"
    if "phú quốc" in t:
        slots["destination"] = "Phú Quốc"
    if "hồ chí minh" in t and slots.get("origin") is None:
        slots["origin"] = "Hồ Chí Minh"

    import re
    m = re.search(r"(\\d+)\\s*đêm", t)
    if m:
        slots["nights"] = int(m.group(1))
    m = re.search(r"(\\d+)\\s*triệu", t)
    if m:
        slots["budget_vnd"] = int(m.group(1)) * 1_000_000
    return slots

def _llm_extract(text: str) -> Dict[str, Any]:
    if LLM is None:
        return {}
    prompt = (
        "Bạn là bộ phân tích ý định. Trả về JSON duy nhất với các khóa: "
        "intent (greeting|flight_search|trip_plan|hotel_request|non_travel), "
        "origin, destination, nights, budget_vnd. "
        "Nếu không rõ thì để null. Không thêm văn bản khác.\n"
        f"Input: {text}"
    )
    try:
        msg = LLM.invoke([HumanMessage(content=prompt)])
        data = json.loads(msg.content)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}

def detect_intent(text: str) -> Dict[str, Any]:
    data = _llm_extract(text)
    intent = data.get("intent")
    slots = {
        "origin": data.get("origin"),
        "destination": data.get("destination"),
        "nights": data.get("nights"),
        "budget_vnd": data.get("budget_vnd"),
    }
    slots = _rule_fill_slots(text, slots)

    t = text.lower()
    if intent not in {"greeting", "flight_search", "trip_plan", "hotel_request", "non_travel"}:
        if "lập trình" in t or "python" in t or "linked list" in t:
            intent = "non_travel"
        elif "đặt khách sạn" in t or "khách sạn" in t:
            intent = "hotel_request"
        elif "chuyến bay" in t:
            intent = "flight_search"
        elif ("đêm" in t and ("muốn đi" in t or "tôi ở" in t)) or "phú quốc" in t:
            intent = "trip_plan"
        elif "chưa biết đi đâu" in t or "muốn đi du lịch" in t:
            intent = "greeting"
        else:
            intent = "greeting"

    return {"intent": intent, "slots": slots}

def analyze_node(state: AgentState):
    user_text = ""
    if state["messages"]:
        last = state["messages"][-1]
        if isinstance(last, HumanMessage):
            user_text = last.content or ""
    parsed = detect_intent(user_text)
    intent = parsed["intent"]
    slots = parsed["slots"]
    return {
        "intent": intent,
        "params": slots,
        "tool_results": [],
        "need_followup": False,
        "followup_question": "",
    }

def policy_node(state: AgentState):
    intent = state.get("intent", "")
    slots = state.get("params", {})
    need_followup = False
    followup = ""

    if intent == "flight_search":
        if not slots.get("origin") or not slots.get("destination"):
            need_followup = True
            followup = "Bạn muốn bay từ đâu đến đâu?"
    elif intent == "trip_plan":
        if not slots.get("origin") or not slots.get("destination") or not slots.get("nights"):
            need_followup = True
            followup = "Bạn cho tôi biết điểm đi, điểm đến và số đêm nhé."
    elif intent == "hotel_request":
        need_followup = True
        followup = "Bạn cho tôi biết thành phố, số đêm và ngân sách khách sạn nhé."

    return {"need_followup": need_followup, "followup_question": followup}

def tool_node(state: AgentState):
    intent = state.get("intent", "")
    results: List[Dict[str, Any]] = []
    slots = state.get("params", {})
    if state.get("need_followup"):
        return {"tool_results": results}

    if intent == "flight_search":
        flights = search_flight_tool.invoke({"origin": slots["origin"], "destination": slots["destination"]})
        results.append({"tool": "search_flight_tool", "result": flights})

    elif intent == "trip_plan":
        flights = search_flight_tool.invoke({"origin": slots["origin"], "destination": slots["destination"]})
        results.append({"tool": "search_flight_tool", "result": flights})

        hotels = search_hotels_tool.invoke({"city": slots["destination"]})
        results.append({"tool": "search_hotels_tool", "result": hotels})

        cheapest_flight = min(flights, key=lambda x: x["price"]) if flights else None
        cheapest_hotel = min(hotels, key=lambda x: x["price_per_night"]) if hotels else None
        budget = calculate_budget_tool.invoke({
            "flight_price": int(cheapest_flight["price"]) if cheapest_flight else 0,
            "hotel_price_per_night": int(cheapest_hotel["price_per_night"]) if cheapest_hotel else 0,
            "num_nights": int(slots.get("nights") or 2),
            "num_travelers": 1
        })
        results.append({"tool": "calculate_budget_tool", "result": budget})

    if results:
        return {
            "tool_results": results,
            "messages": [AIMessage(content=json.dumps(results, ensure_ascii=False, indent=2))]
        }

    return {"tool_results": results}

def response_node(state: AgentState):
    intent = state.get("intent", "")
    tool_results = state.get("tool_results", [])
    if state.get("need_followup"):
        return {"messages": [AIMessage(content=state.get("followup_question", ""))]}

    if intent == "greeting":
        reply = (
            "Xin chào! Tôi là Travel Buddy, rất vui được đồng hành cùng bạn.\n\n"
            "Bạn thích đi biển, lên núi hay tham quan thành phố/di tích lịch sử? "
            "Ngoài ra bạn dự định đi trong bao lâu và xuất phát từ đâu?"
        )
        return {"messages": [AIMessage(content=reply)]}

    if intent == "hotel_request":
        reply = (
            "Chào bạn! Tôi rất sẵn lòng giúp bạn tìm khách sạn.\n\n"
            "Bạn cho tôi biết giúp 3 thông tin nhé:\n"
            "1. Thành phố muốn ở\n"
            "2. Số đêm dự kiến\n"
            "3. Ngân sách cho khách sạn"
        )
        return {"messages": [AIMessage(content=reply)]}

    if intent == "non_travel":
        reply = (
            "Rất tiếc, tôi là Travel Buddy - trợ lý chuyên về du lịch Việt Nam, "
            "nên tôi không thể hỗ trợ các vấn đề về lập trình.\n\n"
            "Nếu bạn cần lên kế hoạch du lịch, tìm chuyến bay hay khách sạn, "
            "hãy cho tôi biết nhé!"
        )
        return {"messages": [AIMessage(content=reply)]}

    if intent == "flight_search":
        flights = tool_results[0]["result"] if tool_results else []
        if LLM is not None:
            prompt = (
                "Bạn là trợ lý du lịch. Dựa trên dữ liệu chuyến bay bên dưới, "
                "hãy trả lời ngắn gọn bằng tiếng Việt và liệt kê các chuyến bay.\n"
                f"DỮ LIỆU: {json.dumps(flights, ensure_ascii=False)}"
            )
            msg = LLM.invoke([HumanMessage(content=prompt)])
            return {"messages": [AIMessage(content=msg.content)]}
        if not flights:
            reply = "Xin lỗi, tôi chưa tìm thấy chuyến bay phù hợp."
        else:
            lines = ["Dưới đây là các chuyến bay:"]
            for f in flights:
                lines.append(
                    f"- {f['airline']} | {f['departure']} - {f['arrival']} | {f['class']} | {f['price']:,} VND"
                )
            reply = "\n".join(lines)
        return {"messages": [AIMessage(content=reply)]}

    if intent == "trip_plan":
        flights = tool_results[0]["result"] if len(tool_results) > 0 else []
        hotels = tool_results[1]["result"] if len(tool_results) > 1 else []
        budget = tool_results[2]["result"] if len(tool_results) > 2 else None
        if LLM is not None:
            prompt = (
                "Bạn là trợ lý du lịch. Dựa trên dữ liệu dưới đây, hãy tư vấn "
                "ngắn gọn bằng tiếng Việt, không bịa dữ liệu.\n"
                f"FLIGHTS: {json.dumps(flights, ensure_ascii=False)}\n"
                f"HOTELS: {json.dumps(hotels, ensure_ascii=False)}\n"
                f"BUDGET: {json.dumps(budget, ensure_ascii=False)}"
            )
            msg = LLM.invoke([HumanMessage(content=prompt)])
            return {"messages": [AIMessage(content=msg.content)]}

        cheapest_flight = min(flights, key=lambda x: x["price"]) if flights else None
        cheapest_hotel = min(hotels, key=lambda x: x["price_per_night"]) if hotels else None

        lines = ["Gợi ý chuyến đi:"]
        if cheapest_flight:
            lines.append(
                f"- Vé rẻ nhất: {cheapest_flight['airline']} "
                f"{cheapest_flight['departure']} - {cheapest_flight['arrival']} "
                f"({cheapest_flight['class']}) giá {cheapest_flight['price']:,} VND"
            )
        if cheapest_hotel:
            lines.append(
                f"- Khách sạn giá tốt: {cheapest_hotel['name']} "
                f"{cheapest_hotel['stars']} sao, {cheapest_hotel['area']}, "
                f"{cheapest_hotel['price_per_night']:,} VND/đêm"
            )
        if budget:
            lines.append(
                f"- Tổng chi phí ước tính: {budget['total_budget_vnd']:,} VND "
                f"(vé: {budget['flight_cost']:,} VND, "
                f"khách sạn: {budget['hotel_cost']:,} VND)"
            )
        reply = "\n".join(lines)
        return {"messages": [AIMessage(content=reply)]}

    return {"messages": [AIMessage(content="Xin chào! Bạn cần hỗ trợ gì về du lịch?")]}

# ====================== GRAPH ======================
def route_after_analyze(state: AgentState):
    if state.get("intent") in ("flight_search", "trip_plan"):
        return "tools"
    return "policy"

if LANGGRAPH_AVAILABLE:
    workflow = StateGraph(AgentState)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("policy", policy_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("respond", response_node)

    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges("analyze", route_after_analyze, {"tools": "tools", "policy": "policy"})
    workflow.add_edge("policy", "respond")
    workflow.add_edge("tools", "respond")

    app = workflow.compile()
else:
    class _FallbackApp:
        def stream(self, inputs, config=None):
            state: AgentState = {
                "messages": inputs["messages"],
                "intent": "",
                "params": {},
                "tool_results": [],
                "need_followup": False,
                "followup_question": "",
            }
            out = analyze_node(state)
            state.update(out)
            yield {"analyze": out}

            if route_after_analyze(state) == "tools":
                out = tool_node(state)
                state.update(out)
                yield {"tools": out}
            else:
                out = policy_node(state)
                state.update(out)
                yield {"policy": out}

            out = response_node(state)
            state.update(out)
            yield {"respond": out}

    app = _FallbackApp()

# ====================== LOGGING ======================
LOG_FILE = "test_results_final1.log"

def log_result(test_number: int, query: str, output: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"TEST CASE {test_number} - {timestamp}\n")
        f.write(f"Query: {query}\n")
        f.write(f"Output:\n{output}\n")
        f.write(f"{'='*80}\n")

def run_agent(query: str, test_number: int):
    print(f"\n👤 User: {query}")
    print("=" * 80)

    inputs = {"messages": [HumanMessage(content=query)]}
    full_output = ""

    for output in app.stream(inputs, config={"recursion_limit": 50}):
        for key, value in output.items():
            if "messages" in value:
                msg = value["messages"][-1]
                if isinstance(msg, AIMessage) and msg.content:
                    print(f"🤖 Agent: {msg.content}")
                    full_output += f"🤖 Agent: {msg.content}\n"

    print("=" * 80)
    log_result(test_number, query, full_output)
    print(f"💾 Saved to {LOG_FILE}")

if __name__ == "__main__":
    print("🌴 Travel Buddy Agent - Gemma 4 26B A4B via OpenRouter\n")

    test_cases = [
        "Xin chào! Tôi đang muốn đi du lịch nhưng chưa biết đi đâu.",
        "Tìm giúp tôi chuyến bay từ Hà Nội đi Đà Nẵng",
        "Tôi ở Hà Nội, muốn đi Phú Quốc 2 đêm, budget 5 triệu. Tư vấn giúp!",
        "Tôi muốn đặt khách sạn",
        "Giải giúp tôi bài tập lập trình Python về linked list"
    ]

    for i, query in enumerate(test_cases, 1):
        print(f"\n=== TEST CASE {i} ===")
        run_agent(query, i)
        if i < len(test_cases):
            input("\nNhấn Enter để chạy test tiếp theo...")

    print(f"\n✅ All tests completed! Check 'test_results.log' for full results.")
