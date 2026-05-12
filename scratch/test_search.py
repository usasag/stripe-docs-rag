import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.deps import search_service_dep

def main():
    service = search_service_dep()
    query = "What is the difference between a SetupIntent and a PaymentIntent in Stripe?"
    print(f"Searching for: {query}")
    try:
        results = service.search(query=query, top_k=5)
        print("RESULTS:", results)
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    main()
