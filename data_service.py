from io import StringIO
import pandas as pd
import numpy as np
import requests

def get_sheet(writer, condition, sponsor):
    params = {
        "query.cond": condition, 
        "query.spons": sponsor,
        "pageSize": 1000, 
        "format": "csv",
        "sort": "StudyFirstPostDate:desc"
    }

    response = requests.get("https://clinicaltrials.gov/api/v2/studies", params=params)

    if response.status_code != 200:
        print(f"Error fetching data: {response.text}")

    data = StringIO(response.text)
    output = pd.read_csv(data)

    # adds day to YYYY-MM-DD if missing
    for column in ["Start Date", "Primary Completion Date", "Completion Date"]:
        mask = output[column].str.len() == 7
        output.loc[mask, column] = output[column].astype(str) + "-01"
            
    output.insert(8, "Conditions (revised)", [condition] * output.shape[0]) # adds conditions revision column 
    output.insert(24, "Start Year", output["Start Date"].str.slice(0, 4)) # adds start year column

    # converts str dates to datetime objs
    output[["Start Date","Completion Date"]] = output[["Start Date","Completion Date"]].apply(pd.to_datetime, errors="coerce")
    output.insert(27, "Duration (mos)", round((output["Completion Date"] - output["Start Date"]) / np.timedelta64(30, "D"))) # adds duration column 

    # converts datetime columns back to strings for the sheet
    output["Start Date"] = output["Start Date"].dt.strftime("%Y-%m-%d")
    output["Completion Date"] = output["Completion Date"].dt.strftime("%Y-%m-%d")

    output.to_excel(writer, sheet_name=condition, index=False) 
            
    return output