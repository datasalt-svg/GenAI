import psycopg2
import pandas as pd
from sklearn.preprocessing import StandardScaler

# Database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = 'postgres123'
TABLE_NAME = 'party'

def fetch_data():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    query = f"SELECT * FROM {TABLE_NAME};"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def standardize_data(df, columns=None):
    scaler = StandardScaler()
    if columns is None:
        columns = df.select_dtypes(include=['float64', 'int64']).columns
    df[columns] = scaler.fit_transform(df[columns])
    return df

if __name__ == "__main__":
    df = fetch_data()
    print("Original Data:")
    print(df.head())

    standardized_df = standardize_data(df)
    print("\nStandardized Data:")
    print(standardized_df.head())