import duckdb

conn = duckdb.connect('stylehub_dbt/stylehub.db')

print("Loading data into DuckDB...")

#load CSVs 
conn.execute("DROP TABLE IF EXISTS products")
conn.execute("DROP TABLE IF EXISTS customers")
conn.execute("DROP TABLE IF EXISTS sessions")
conn.execute("DROP TABLE IF EXISTS orders")

conn.execute("CREATE TABLE products AS SELECT * FROM read_csv_auto('../data/products.csv')")
conn.execute("CREATE TABLE customers AS SELECT * FROM read_csv_auto('../data/customers.csv')")
conn.execute("CREATE TABLE sessions AS SELECT * FROM read_csv_auto('../data/sessions.csv')")
conn.execute("CREATE TABLE orders AS SELECT * FROM read_csv_auto('../data/orders.csv')")

#sanity check
print("\nTables loaded:")
for table in ['products', 'customers', 'sessions', 'orders']:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f" {table}: {count:,} rows")

#show schemas
print("\nShowing TABLES:")
result = conn.execute("SHOW TABLES").fetchall()
for row in result:
    print(f" - {row[0]}")

conn.close()
print("\nData loaded successfully!")
print("\nNow run commands: dbt run")