import streamlit as st
import numpy as np
import pandas as pd
from pymongo import MongoClient
import datetime
import base64
from io import BytesIO




@st.cache
def get_companies():
    return list(db.Company.find())
@st.cache
def get_vessels(company_id):
    return list(db.Vessel.find({"companyId": company_id}))
@st.cache
def get_bunkerItems():
    return list(db.BunkerItem.find().sort("startTime", -1))

@st.cache
def get_FuelType(vessel_id, fuel_id):
    return list(db.FuelType.find({"vesselId": vessel_id, "pkId": fuel_id}))

@st.cache
def get_bunkerValues(bunkerItemId):
    return list(db.BunkerMeasurement.aggregate(
        [
            {
                '$match': {
                    'bunkerItemId': bunkerItemId
                }
            }
        ]
    ))

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1')
    writer.save()
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    val = to_excel(df)
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="extract.xlsx">Download csv file</a>'

st.sidebar.title("Bunker Downloader")
st.sidebar.markdown("### Connect:")
url = st.sidebar.text_input("URL", value="10.100.42.216")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type='password')

if url and username and password:
    ecomate = MongoClient(f"mongodb://{username}:{password}@{url}/ecomate?authSource=admin")
    db = ecomate.get_database()
else:
    db = None
if(db):
    st.sidebar.markdown("### Choose:")

    companies = get_companies()
    company = st.sidebar.selectbox("Choose a company", companies, format_func=lambda v: v["name"])
    vessels_list = get_vessels(company["pkId"])
    vessel = st.sidebar.selectbox("Choose a Vessel",
                              vessels_list, format_func=lambda v: v["name"])
    bunkers = get_bunkerItems()
    bunker = st.sidebar.selectbox("Choose a bunker", bunkers, format_func=lambda v: v["startTime"])
    bunker_measurements = get_bunkerValues(bunker["pkId"])
    out = {m["type"]: m["values"] for m in bunker_measurements}
    index = bunker['startTime'] + np.arange(len(out["MassFlow"])) * datetime.timedelta(seconds=1)
    df = pd.DataFrame(out, index=index)

    st.markdown(f"### {vessel['name']}")
    st.markdown(f"**{bunker['startTime'].strftime('%d %b %Y, %H:%M')}** - **{bunker['endTime'].strftime('%d %b %Y, %H:%M')}**")

    st.markdown(get_table_download_link(df), unsafe_allow_html=True)

    filtered = [{"Key": k, "Value": bunker[k]} for k in bunker.keys() if "_" not in k]
    bunker_pd = pd.DataFrame(filtered)

    st.markdown("### Bunker Data")
    st.line_chart(df)

    st.markdown("### Bunker details")
    bunker_pd

    st.markdown("### Fuel details")
    fuels = get_FuelType(bunker["vesselId"], bunker["fuelTypeId"])
    for f in fuels:
        st.markdown(f"Name: ** {f['name']}**")
        st.markdown(f"Category: ** {f['category']} **")
        st.markdown(f"CO2 Emission Factor: ** {f['CO2EmissionFactor']} **")
        st.markdown(f"sulphur Content ** {f['sulphurContent']} **")


    st.markdown("---")
    for bm in bunker_measurements:
        st.markdown(f"### {bm['type']}")
        st.line_chart(df[bm["type"]])
