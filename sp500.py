import pandas as pd

# Read the CSV file into a DataFrame
df = pd.read_csv('sp500_companies.csv')

# Select a reduced set of columns
reduced_df = df[['Symbol', 'Weight']]

# Print the reduced DataFrame
# print(reduced_df)

for index, row in reduced_df.iterrows():
    print(row['Symbol'], row['Weight']*90000)
