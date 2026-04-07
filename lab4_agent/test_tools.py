# test_tools.py
from tools import FLIGHTS_DB, HOTELS_DB, search_flight

print("=" * 50)
print("✅ Testing tools.py ...")
print("=" * 50)

print("Number of routes in FLIGHTS_DB:", len(FLIGHTS_DB))
print("Cities with hotels:", list(HOTELS_DB.keys()))

flights = search_flight("Hà Nội", "Đà Nẵng")
print("Flights from Hà Nội to Đà Nẵng:", len(flights))

if flights and isinstance(flights, list):
    print("\nSample flight:")
    print(flights[0])
else:
    print("\nError:", flights)

print("\n✅ Test completed!")