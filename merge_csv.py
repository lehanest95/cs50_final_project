import glob
import os
import time
from datetime import datetime
import numpy as np

import pandas as pd
from sys import exit
import csv_to_sqlite

print("\n\n\nmerged.csv will be written to the same directory of 'merged_csv.py'")
print("Please ENSURE FOLDER containing CSVs is in the same directory and called 'CSVs'")
# process = input("Start processing? (y/n) : ")
# if process == "n":
#     exit(0)
path = "/CSVs"
current_dir = str(os.path.dirname(os.path.abspath(__file__)))
path = current_dir + path

# get list of all files in the folder which correspond to Intro to CS50 topics from Discord CSVs
all_files = glob.glob(os.path.join(path, "cs50 - CS50x - Intro to CS*.csv"))

# list to store all CSVs contents
all_df = []
for f in all_files:
    df = pd.read_csv(f, sep=',')  # read contents of particular CSV (including headers)
    df['file'] = f.split('/')[-1]  # add new column named "file" and put in the name of the file
    # df['unix'] = 1
    all_df.append(df)  # add contents to the list

# merge all (remove headers from subsequent CSVs)
merged_df = pd.concat(all_df, ignore_index=True, sort=True)

for index, row in merged_df.iterrows():
    # print(row['Date'])
    # convert to datetime format (object)
    datetime_object = datetime.strptime(row['Date'], '%d-%b-%y %I:%M %p')
    # convert to unix
    datetime_object = time.mktime(datetime_object.timetuple())
    # row['Date'] = datetime_object
    # print(row['unix'])
    row['unix'] = datetime_object
    # print(row['unix'])
    # print(row['Date'])

print(merged_df['unix'])

# write to new CSV
# merged_df.to_csv("merged.csv", date_format='%Y%m%d')
merged_df.to_csv("merged.csv")
print("merged.csv successfully written!")

# write CSV to database

csv_merged = pd.read_csv("merged.csv")

# https://pypi.org/project/csv-to-sqlite/
options = csv_to_sqlite.CsvOptions(typing_style="full", encoding="utf-8")
input_files = ["merged.csv"]  # pass in a list of CSV files
csv_to_sqlite.write_csv(input_files, "merged.db", options)


exit(0)
