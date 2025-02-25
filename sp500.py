import pandas as pd

# Use the Kaggle dataset. https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks?resource=download

# Read the CSV file into a DataFrame
df = pd.read_csv('sp500_companies.csv')

# Select a reduced set of columns
reduced_df = df[['Symbol', 'Weight']]

# Print the reduced DataFrame
# print(reduced_df)

for index, row in reduced_df.iterrows():
    print(row['Symbol'], row['Weight']*90000)
