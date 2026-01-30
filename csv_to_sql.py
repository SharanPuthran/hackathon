#!/usr/bin/env python3
"""
Convert CSV files to SQL INSERT statements
"""

import csv
import os

def escape_sql_value(value):
    """Escape special characters for SQL"""
    if value is None or value == '':
        return 'NULL'
    
    # Try to convert to number
    try:
        if '.' in str(value):
            float(value)
            return str(value)
        else:
            int(value)
            return str(value)
    except (ValueError, TypeError):
        pass
    
    # String value - escape single quotes
    value = str(value).replace("'", "''")
    return f"'{value}'"

def csv_to_sql(csv_file, table_name, output_file, batch_size=100):
    """Convert CSV to SQL INSERT statements"""
    print(f"Converting {csv_file} to SQL INSERTs...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        if not rows:
            print(f"  No data in {csv_file}")
            return
        
        columns = list(rows[0].keys())
        
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(f"-- INSERT statements for {table_name}\n")
            out.write(f"-- Total records: {len(rows)}\n\n")
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                
                # Build multi-row INSERT
                out.write(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES\n")
                
                for j, row in enumerate(batch):
                    values = [escape_sql_value(row[col]) for col in columns]
                    values_str = ', '.join(values)
                    
                    if j < len(batch) - 1:
                        out.write(f"  ({values_str}),\n")
                    else:
                        out.write(f"  ({values_str});\n\n")
        
        print(f"  Created {output_file} with {len(rows)} records")

def main():
    """Convert all CSV files to SQL"""
    csv_dir = 'output'
    sql_dir = 'sql_inserts'
    
    os.makedirs(sql_dir, exist_ok=True)
    
    # Mapping of CSV files to table names
    csv_to_table = {
        'flights.csv': 'flights',
        'passengers.csv': 'passengers',
        'bookings.csv': 'bookings',
        'baggage.csv': 'baggage',
        'cargo_shipments.csv': 'cargo_shipments',
        'cargo_flight_assignments.csv': 'cargo_flight_assignments',
        'crew_members.csv': 'crew_members',
        'crew_roster.csv': 'crew_roster',
    }
    
    print("=" * 60)
    print("CSV to SQL Converter")
    print("=" * 60)
    print()
    
    for csv_file, table_name in csv_to_table.items():
        csv_path = os.path.join(csv_dir, csv_file)
        sql_path = os.path.join(sql_dir, f"{table_name}_inserts.sql")
        
        if os.path.exists(csv_path):
            csv_to_sql(csv_path, table_name, sql_path)
        else:
            print(f"Warning: {csv_path} not found")
    
    # Create master import file
    master_file = os.path.join(sql_dir, 'import_all.sql')
    with open(master_file, 'w', encoding='utf-8') as f:
        f.write("-- Master import file for all tables\n")
        f.write("-- Run this after creating the database schema\n\n")
        
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
        
        for table_name in csv_to_table.values():
            f.write(f"SOURCE {table_name}_inserts.sql;\n")
        
        f.write("\nSET FOREIGN_KEY_CHECKS = 1;\n")
    
    print()
    print("=" * 60)
    print(f"SQL files created in '{sql_dir}/' directory")
    print(f"Run 'SOURCE {sql_dir}/import_all.sql' in MySQL to import all data")
    print("=" * 60)

if __name__ == '__main__':
    main()
