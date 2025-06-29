#!/usr/bin/env python3
"""
Test script to verify budget plans API endpoints work correctly.
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_budget_plans_api():
    """Test budget plans API endpoints"""
    
    print("🧪 Testing Budget Plans API")
    print("=" * 50)
    
    # Test 1: List budget plans (should be empty initially)
    print("\n1. Testing GET /budget-plans")
    try:
        response = requests.get(f"{BASE_URL}/budget-plans")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            plans = response.json()
            print(f"✅ Success: Found {len(plans)} budget plans")
        else:
            print(f"❌ Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the backend server running on port 8000?")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Get categories (needed for creating budget plans)
    print("\n2. Testing GET /categories")
    try:
        response = requests.get(f"{BASE_URL}/categories")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            categories = response.json()
            print(f"✅ Success: Found {len(categories)} categories")
            if categories:
                category_id = categories[0]['id']
                print(f"Using category: {categories[0]['name']} (ID: {category_id})")
            else:
                print("❌ No categories found - cannot test budget plan creation")
                return
        else:
            print(f"❌ Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 3: Create a budget plan
    print("\n3. Testing POST /budget-plans")
    try:
        plan_data = {
            "category_id": category_id,
            "name": "Test Monthly Budget",
            "type": "REGULAR",
            "start_date": datetime.now().isoformat(),
            "end_date": None,
            "recurrence": "MONTHLY",
            "rollover_policy": "NONE",
            "max_amount": 1000.0,
            "alert_thresholds": None,
            "tags": None
        }
        
        response = requests.post(
            f"{BASE_URL}/budget-plans",
            json=plan_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            created_plan = response.json()
            print(f"✅ Success: Created budget plan with ID: {created_plan['id']}")
            plan_id = created_plan['id']
        else:
            print(f"❌ Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 4: Get the created budget plan
    print(f"\n4. Testing GET /budget-plans/{plan_id}")
    try:
        response = requests.get(f"{BASE_URL}/budget-plans/{plan_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            plan = response.json()
            print(f"✅ Success: Retrieved budget plan: {plan['name']}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Generate budget periods
    print(f"\n5. Testing POST /budget-plans/generate-periods/{plan_id}")
    try:
        response = requests.post(f"{BASE_URL}/budget-plans/generate-periods/{plan_id}?months_ahead=3")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result['message']}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: List budget plans again (should now have our created plan)
    print("\n6. Testing GET /budget-plans (after creation)")
    try:
        response = requests.get(f"{BASE_URL}/budget-plans")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            plans = response.json()
            print(f"✅ Success: Found {len(plans)} budget plans")
            for plan in plans:
                print(f"  - {plan['name']} ({plan['type']}) - {len(plan['periods'])} periods")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 7: Consolidated budget view
    print("\n7. Testing GET /budget-plans/consolidated/view")
    try:
        start_date = datetime.now().replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        response = requests.get(f"{BASE_URL}/budget-plans/consolidated/view", params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            consolidated = response.json()
            print(f"✅ Success: Consolidated view - ${consolidated['total_allocated']} allocated")
            print(f"  Categories: {len(consolidated['categories'])}")
            print(f"  Budget plans: {len(consolidated['budget_plans'])}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Budget Plans API test completed!")

if __name__ == "__main__":
    test_budget_plans_api()