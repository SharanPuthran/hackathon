#!/usr/bin/env python3
"""
Verify operational data access remains unchanged after checkpoint integration
"""

import sys
sys.path.insert(0, 'src')

from database.dynamodb import DynamoDBClient

def test_dynamodb_client():
    """Test that DynamoDBClient still works correctly"""
    print("\n" + "="*60)
    print("OPERATIONAL DATA ACCESS VERIFICATION")
    print("="*60)
    
    try:
        # Initialize client
        client = DynamoDBClient()
        print("✅ DynamoDBClient initialized")
        
        # Test table access
        tables = [
            "flights",
            "CrewRoster",
            "CargoShipments",
            "passengers",
            "bookings"
        ]
        
        for table_name in tables:
            try:
                # Try to access table
                table = client.dynamodb.Table(table_name)
                # Get item count
                response = table.scan(Select='COUNT', Limit=1)
                print(f"✅ Table accessible: {table_name}")
            except Exception as e:
                print(f"❌ Table error: {table_name} - {e}")
                return False
        
        print("\n✅ All operational tables accessible")
        print("✅ DynamoDBClient working correctly")
        print("✅ Checkpoint integration did NOT affect operational data access")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_dynamodb_client()
    sys.exit(0 if success else 1)
