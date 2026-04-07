import unittest
from typing import Dict, List, Any

# ========================== DATABASES (Copy from your images) ==========================
FLIGHTS_DB: Dict[tuple, List[Dict]] = {
    ("Hà Nội", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "07:20", "price": 1_450_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "14:00", "arrival": "15:20", "price": 2_800_000, "class": "business"},
        {"airline": "VietJet Air", "departure": "08:30", "arrival": "09:50", "price": 890_000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "11:00", "arrival": "12:20", "price": 1_200_000, "class": "economy"},
    ],
    ("Hà Nội", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "07:00", "arrival": "09:15", "price": 2_100_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "10:00", "arrival": "12:15", "price": 1_350_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "16:00", "arrival": "18:15", "price": 1_100_000, "class": "economy"},
    ],
    ("Hà Nội", "Hồ Chí Minh"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "08:10", "price": 1_600_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "07:30", "arrival": "09:40", "price": 950_000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "12:00", "arrival": "14:10", "price": 1_300_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "18:00", "arrival": "20:10", "price": 3_200_000, "class": "business"},
    ],
    ("Hồ Chí Minh", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "09:00", "arrival": "10:20", "price": 1_300_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "13:00", "arrival": "14:20", "price": 780_000, "class": "economy"},
    ],
    ("Hồ Chí Minh", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "08:00", "arrival": "09:00", "price": 1_100_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "15:00", "arrival": "16:00", "price": 650_000, "class": "economy"},
    ],
}

HOTELS_DB: Dict[str, List[Dict]] = {
    "Đà Nẵng": [
        {"name": "Mường Thanh Luxury", "stars": 5, "price_per_night": 1_800_000, "area": "Mỹ Khê", "rating": 4.5},
        {"name": "Sala Danang Beach", "stars": 4, "price_per_night": 1_200_000, "area": "Mỹ Khê", "rating": 4.3},
        {"name": "Fivitel Danang", "stars": 3, "price_per_night": 650_000, "area": "Sơn Trà", "rating": 4.1},
        {"name": "Memory Hostel", "stars": 2, "price_per_night": 250_000, "area": "Hải Châu", "rating": 4.6},
        {"name": "Christina's Homestay", "stars": 2, "price_per_night": 350_000, "area": "An Thượng", "rating": 4.7},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Resort", "stars": 5, "price_per_night": 3_500_000, "area": "Bãi Dài", "rating": 4.4},
        {"name": "Sol by Melia", "stars": 4, "price_per_night": 1_500_000, "area": "Bãi Trường", "rating": 4.2},
        {"name": "Lahana Resort", "stars": 3, "price_per_night": 800_000, "area": "Dương Đông", "rating": 4.0},
        {"name": "9Station Hostel", "stars": 2, "price_per_night": 200_000, "area": "Dương Đông", "rating": 4.5},
    ],
    "Hồ Chí Minh": [
        {"name": "Rex Hotel", "stars": 5, "price_per_night": 2_800_000, "area": "Quận 1", "rating": 4.3},
        {"name": "Liberty Central", "stars": 4, "price_per_night": 1_400_000, "area": "Quận 1", "rating": 4.1},
        {"name": "Cochin Zen Hotel", "stars": 3, "price_per_night": 550_000, "area": "Quận 1", "rating": 4.4},
        {"name": "The Common Room", "stars": 2, "price_per_night": 180_000, "area": "Quận 1", "rating": 4.6},
    ],
}

# ========================== HELPER FUNCTIONS (Your Tools) ==========================
def search_flights(origin: str, destination: str) -> List[Dict]:
    """Tool to search flights"""
    key = (origin.strip(), destination.strip())
    return FLIGHTS_DB.get(key, [])

def search_hotels(city: str, min_stars: int = 1, max_price: int = None, min_rating: float = 0.0) -> List[Dict]:
    """Tool to search hotels with filters"""
    hotels = HOTELS_DB.get(city.strip(), [])
    result = []
    for h in hotels:
        if (h["stars"] >= min_stars and 
            (max_price is None or h["price_per_night"] <= max_price) and 
            h["rating"] >= min_rating):
            result.append(h)
    return result

# ========================== UNIT TESTS ==========================
class TestTravelAgent(unittest.TestCase):

    # ==================== Flight Tests ====================
    def test_01_flights_hanoi_to_danang(self):
        """Test Case 1: Basic flight search from Hà Nội to Đà Nẵng"""
        flights = search_flights("Hà Nội", "Đà Nẵng")
        self.assertEqual(len(flights), 4)
        self.assertIn("VietJet Air", [f["airline"] for f in flights])
        print("✓ Test 1 passed: Found 4 flights from Hà Nội to Đà Nẵng")

    def test_02_cheapest_flight_hcm_to_phuquoc(self):
        """Test Case 2: Find cheapest flight"""
        flights = search_flights("Hồ Chí Minh", "Phú Quốc")
        cheapest = min(flights, key=lambda x: x["price"])
        self.assertEqual(cheapest["price"], 650_000)
        self.assertEqual(cheapest["airline"], "VietJet Air")
        print("✓ Test 2 passed: Cheapest flight is 650,000 VND")

    def test_03_business_class_hanoi_to_hcm(self):
        """Test Case 3: Filter by class"""
        flights = search_flights("Hà Nội", "Hồ Chí Minh")
        business = [f for f in flights if f["class"] == "business"]
        self.assertEqual(len(business), 1)
        self.assertEqual(business[0]["price"], 3_200_000)
        print("✓ Test 3 passed: Business class found")

    # ==================== Hotel Tests ====================
    def test_04_five_star_hotels_phuquoc(self):
        """Test Case 4: 5-star hotels in Phú Quốc"""
        hotels = search_hotels("Phú Quốc", min_stars=5)
        self.assertEqual(len(hotels), 1)
        self.assertEqual(hotels[0]["name"], "Vinpearl Resort")
        print("✓ Test 4 passed: Found 5-star hotel in Phú Quốc")

    def test_05_budget_high_rating_danang(self):
        """Test Case 5: High-rated budget hotels in Đà Nẵng"""
        hotels = search_hotels("Đà Nẵng", max_price=400_000, min_rating=4.5)
        self.assertGreaterEqual(len(hotels), 2)
        names = [h["name"] for h in hotels]
        self.assertIn("Christina's Homestay", names)
        print("✓ Test 5 passed: Found high-rated budget hotels in Đà Nẵng")

    # ==================== Combined Logic Tests ====================
    def test_06_total_budget_hanoi_to_danang(self):
        """Test Case 6: Flight + 1 night hotel under budget"""
        flights = search_flights("Hà Nội", "Đà Nẵng")
        hotels = search_hotels("Đà Nẵng", max_price=600_000)
        
        cheapest_flight = min(flights, key=lambda x: x["price"])
        cheapest_hotel = min(hotels, key=lambda x: x["price_per_night"]) if hotels else None
        
        total = cheapest_flight["price"] + (cheapest_hotel["price_per_night"] if cheapest_hotel else 0)
        self.assertLessEqual(total, 2_000_000)
        print(f"✓ Test 6 passed: Total budget = {total:,} VND (under 2M)")

    def test_07_no_flight_found(self):
        """Test Case 7: Handle non-existent route"""
        flights = search_flights("Đà Nẵng", "Hà Nội")
        self.assertEqual(len(flights), 0)
        print("✓ Test 7 passed: No flight found for reverse route (as expected)")

    # ==================== LangChain-specific Tests ====================
    def test_08_multi_criteria_hotel(self):
        """Test Case 8: Multi-criteria hotel filtering (for LLM post-processing)"""
        hotels = search_hotels("Hồ Chí Minh", min_stars=3, min_rating=4.0)
        self.assertGreaterEqual(len(hotels), 2)
        print("✓ Test 8 passed: Multi-criteria hotel filter works")

    def test_09_compare_airlines(self):
        """Test Case 9: Prepare data for airline comparison (useful for LLM)"""
        flights = search_flights("Hà Nội", "Đà Nẵng")
        vietnam = [f for f in flights if f["airline"] == "Vietnam Airlines"]
        vietjet = [f for f in flights if f["airline"] == "VietJet Air"]
        
        self.assertGreater(len(vietnam), 0)
        self.assertGreater(len(vietjet), 0)
        print("✓ Test 9 passed: Data ready for airline comparison")

    def test_10_all_cities_available(self):
        """Test Case 10: Check supported cities"""
        flight_cities = set()
        for orig, dest in FLIGHTS_DB.keys():
            flight_cities.add(orig)
            flight_cities.add(dest)
        
        hotel_cities = set(HOTELS_DB.keys())
        
        self.assertIn("Hà Nội", flight_cities)
        self.assertIn("Đà Nẵng", hotel_cities)
        print("✓ Test 10 passed: All major cities are covered in DBs")


if __name__ == "__main__":
    unittest.main(verbosity=2)