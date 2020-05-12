import glob
import os

import pandas as pd
from sys import exit

print("\n\n\nmerged.csv will be written to the same directory of 'merged_csv.py'")
print("Please ENSURE FOLDER containing CSVs is in the same directory and called 'CSVs'")
process = input("Start processing? (y/n) : ")
if process == "n":
    exit(0)
path = "/CSVs"
current_dir = str(os.path.dirname(os.path.abspath(__file__)))
path = current_dir + path

# get list of all files in the folder which correspond to Intro to CS50 topics from Discord CSVs
all_files = glob.glob(os.path.join(path, "cs50 - CS50x - Intro to CS*.csv"))

# list to store all CSVs contents
all_df = []
for f in all_files:
    # read contents of particular CSV (including headers)
    df = pd.read_csv(f, sep=',')
    # add new column named "file" and put in the name of the file
    df['file'] = f.split('/')[-1]
    # add contents to the list
    all_df.append(df)

# merge all (remove headers from subsequent CSVs)
merged_df = pd.concat(all_df, ignore_index=True, sort=True)

# write to new CSV
merged_df.to_csv("merged.csv")
print("merged.csv successfully written!")
exit(0)
