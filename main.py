from pivot_services import get_first_pivot, get_second_pivot, get_third_pivot, colour_cols, colour_mean
from data_service import get_sheet
from flask import Flask, render_template, request, send_file, flash
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
@app.route("/", methods = ["GET", "POST"]) 
def index():   
    last_modified = datetime.today().strftime("%Y-%m-%d %I:%M %p") 
    error = ""

    conditions = []
    sponsors = []
    alerts = {}
    result_alerts = {}

    searched = False
    past_search = False
    
    pivot_min_max = {}    
    current_row = 1
    current_historical_row = 1
    current_revenue_row = 1
    current_column = 1
        
    # gets input for search terms from frontend 
    if request.method == "POST":
        # strips whitespace from input 
        conditions = [cond.strip() for cond in request.form.get("conditions", "").split(",") if cond.strip()]
        sponsor_array = [spons.strip() for spons in request.form.get("sponsors", "").split(",") if spons.strip()]

        # joins sponsors for search params
        sponsors = " OR ".join(sponsor_array)

    # runs program if required search term, conditions, is filled 
    if conditions:
        # if file already exists, gets date of past search 
        if os.path.isfile("clinicaltrials.xlsx"):
            last_modified_timestamp = os.path.getmtime("clinicaltrials.xlsx")
            last_modified = datetime.fromtimestamp(last_modified_timestamp).strftime("%Y-%m-%d %I:%M %p")
            past_search = True 

        try:
        # adds all sheets into one file instead of separate file 
            with pd.ExcelWriter("clinicaltrials.xlsx") as writer:
                dedup = []  # empty array to store dataframes

                # iterates through each search term, makes seperate sheet for each
                for condition in conditions:
                    sheet_data = get_sheet(writer, condition, sponsors)
                    dedup.append(sheet_data)

                # adds sheets to combined dedup
                dedup = pd.concat(dedup, ignore_index=True)
                
                # deletes duplicate rows 
                dedup = dedup.drop_duplicates(subset=["NCT Number"], keep="first")
                dedup.to_excel(writer, sheet_name="Combined Dedup", index=False)

                # shows new trials or results posted from last search
                if past_search:
                    date = last_modified[:10]
                    for index, row in dedup.iterrows():
                        # new trials
                        if row["First Posted"] > date:
                            alerts[row["Study Title"]] = {
                                "Study URL": row["Study URL"],
                                "First Posted": row["First Posted"],
                                "Condition": row["Conditions (revised)"],
                                "Sponsors": row["Sponsor"],
                                "Collaborators": "" if pd.isna(row.get("Collaborators")) else "|" + row["Collaborators"]
                            }

                        # new results
                        if pd.notna(row["Results First Posted"]) and row["Results First Posted"] > date: 
                            result_alerts[row["Study Title"]] = {
                                "Study URL": row["Study URL"],
                                "Results First Posted": row["Results First Posted"],
                                "Condition": row["Conditions (revised)"],
                                "Sponsors": row["Sponsor"],
                                "Collaborators": "" if pd.isna(row.get("Collaborators")) else "|" + row["Collaborators"]
                            }
                else:
                    # first time ever searching means no alerts
                    last_modified = datetime.now().strftime("%Y-%m-%d %I:%M %p")

                # creates empty sheets for pivot tables
                writer.book.create_sheet("Pivot by Pharma")
                writer.book.create_sheet("Revenue Insights")
                writer.book.create_sheet("Historical View")
                
                # create overall pivot table with all spons/cond data for Pivot by Pharma
                pivot_all, current_row = get_first_pivot(writer, dedup, "Overall", current_row)
                
                # creates spons-filtered dedups and pivot tables
                for sponsor in sponsor_array:
                    sponsor_dedup = dedup[(
                        dedup["Sponsor"].str.contains(sponsor, case=False, na=False)) | 
                        (dedup["Collaborators"].str.contains(sponsor, case=False, na=False))]
                    
                    sponsor_pivot, current_row = get_first_pivot(writer, sponsor_dedup, sponsor, current_row)
                    sponsor_pivot, current_column, pivot_min_max, current_revenue_row = get_second_pivot(writer, sponsor_dedup, sponsor, current_column, current_revenue_row, conditions, pivot_min_max)
                    sponsor_pivot, current_historical_row = get_third_pivot(writer, sponsor_dedup, sponsor, current_historical_row)

                # colours mean for Revenue Insights
                for sponsor in pivot_min_max:
                    colour_mean(writer.book["Revenue Insights"], pivot_min_max, sponsor)

        # error handling
        except PermissionError:
            error = "The excel file is still open in another program. Close it and try searching again."

        except IndexError:
            error = "No results found. Check spelling and try again."

        # triggers display message in HTML
        searched = True

    # runs index.html with updated variables 
    return render_template("index.html", 
                           searched=searched, 
                           last_modified=last_modified, 
                           alerts=alerts, 
                           result_alerts=result_alerts, 
                           error=error)

# sheet download attachment 
@app.route("/download")
def download_file():
    return send_file("clinicaltrials.xlsx")

if __name__ == "__main__": 
    app.run(host="0.0.0.0", port=3000, debug=False)