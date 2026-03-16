import streamlit as st
import pandas as pd
import datetime
import calendar
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(layout="wide")

st.title("SEO Intelligence Dashboard")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=SCOPES,
)

service = build("searchconsole", "v1", credentials=credentials)

site_url = "https://www.naukrigulf.com"

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------

st.sidebar.header("Filters")

today = datetime.date.today()

months = []
for i in range(12):
    m = today - datetime.timedelta(days=30*i)
    months.append(m.strftime("%Y-%m"))

selected_month = st.sidebar.selectbox(
    "Select Month",
    sorted(set(months), reverse=True)
)

year = int(selected_month.split("-")[0])
month = int(selected_month.split("-")[1])

start_date = datetime.date(year, month, 1)
end_date = datetime.date(year, month, calendar.monthrange(year, month)[1])

if month == 1:
    prev_year = year - 1
    prev_month = 12
else:
    prev_year = year
    prev_month = month - 1

prev_start = datetime.date(prev_year, prev_month, 1)
prev_end = datetime.date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])

device_filter = st.sidebar.selectbox(
    "Device",
    ["All","DESKTOP","MOBILE","TABLET"]
)

section_filter = st.sidebar.selectbox(
    "Website Section",
    ["All","Home","Recruit","Blog","Campus","Career Advice","Resume Maker","Naukri360","Code360","City Jobs","Keyword City Jobs","Keyword Jobs","Other"]
)

keyword_filter = st.sidebar.selectbox(
    "Keyword Type",
    ["All","Brand","Non Brand"]
)

brand_keywords = ["naukri","nakuri","nokri","nokari","naukari","login"]

# -----------------------------
# FETCH DATA
# -----------------------------

def fetch_data(start,end):

    request = {
        "startDate": str(start),
        "endDate": str(end),
        "dimensions": ["query","page","device","date"],
        "rowLimit": 25000
    }

    response = service.searchanalytics().query(
        siteUrl=site_url,
        body=request
    ).execute()

    rows = response.get("rows", [])

    data = []

    for row in rows:
        data.append({
            "keyword": row["keys"][0],
            "page": row["keys"][1],
            "device": row["keys"][2],
            "date": row["keys"][3],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": row["ctr"],
            "position": row["position"]
        })

    return pd.DataFrame(data)

# -----------------------------
# FETCH DATA
# -----------------------------

current_df = fetch_data(start_date,end_date)
prev_df = fetch_data(prev_start,prev_end)

if current_df.empty:
    st.warning("No data found")
    st.stop()

current_df["date"] = pd.to_datetime(current_df["date"])

if not prev_df.empty:
    prev_df["date"] = pd.to_datetime(prev_df["date"])

# -----------------------------
# URL SECTION CLASSIFICATION
# -----------------------------

def classify_page(url):

    if url == "https://www.naukri.com/":
        return "Home"

    if "/recruit/" in url:
        return "Recruit"

    if "/blog/" in url:
        return "Blog"

    if "/campus/" in url:
        return "Campus"

    if "/career-advice/" in url:
        return "Career Advice"

    if "/resume-maker/" in url:
        return "Resume Maker"

    if "/naukri360/" in url:
        return "Naukri360"

    if "/code360/" in url:
        return "Code360"

    if "-jobs-in-" in url:
        return "Keyword City Jobs"

    if "jobs-in" in url:
        return "City Jobs"

    if "-jobs" in url:
        return "Keyword Jobs"

    return "Other"

current_df["section"] = current_df["page"].apply(classify_page)

# -----------------------------
# BRAND CLASSIFICATION
# -----------------------------

def classify_keyword(k):

    k = k.lower()

    for b in brand_keywords:
        if b in k:
            return "Brand"

    return "Non Brand"

current_df["keyword_type"] = current_df["keyword"].apply(classify_keyword)

# -----------------------------
# APPLY FILTERS
# -----------------------------

if device_filter != "All":
    current_df = current_df[current_df["device"]==device_filter]

if section_filter != "All":
    current_df = current_df[current_df["section"]==section_filter]

if keyword_filter != "All":
    current_df = current_df[current_df["keyword_type"]==keyword_filter]

# -----------------------------
# KPI METRICS
# -----------------------------

st.header("SEO Overview")

col1,col2,col3,col4 = st.columns(4)

col1.metric("Clicks",int(current_df["clicks"].sum()))
col2.metric("Impressions",int(current_df["impressions"].sum()))
col3.metric("Avg CTR",round(current_df["ctr"].mean()*100,2))
col4.metric("Avg Position",round(current_df["position"].mean(),2))

# -----------------------------
# BRAND VS NON BRAND
# -----------------------------

st.header("Brand vs Non Brand")

brand_data = current_df.groupby("keyword_type").agg({
    "clicks":"sum",
    "impressions":"sum"
})

st.bar_chart(brand_data)

# -----------------------------
# TOP KEYWORDS
# -----------------------------

st.header("Top Keywords")

top_kw = current_df.groupby("keyword").agg({
    "clicks":"sum",
    "impressions":"sum",
    "position":"mean"
}).sort_values("clicks",ascending=False).head(20)

st.dataframe(top_kw)

# -----------------------------
# QUICK WIN KEYWORDS
# -----------------------------

st.header("Quick Win Keywords")

quick = current_df[
(current_df["position"]>=8) &
(current_df["position"]<=20) &
(current_df["impressions"]>1000)
]

quick_kw = quick.groupby("keyword").agg({
    "clicks":"sum",
    "impressions":"sum",
    "position":"mean"
}).sort_values("impressions",ascending=False).head(20)

st.dataframe(quick_kw)

# -----------------------------
# CTR OPPORTUNITIES
# -----------------------------

st.header("CTR Optimization Opportunities")

ctr_df = current_df[
(current_df["position"]<=5) &
(current_df["ctr"]<0.03)
]

ctr_kw = ctr_df.groupby("keyword").agg({
    "clicks":"sum",
    "impressions":"sum",
    "ctr":"mean",
    "position":"mean"
}).sort_values("impressions",ascending=False).head(20)

st.dataframe(ctr_kw)

# -----------------------------
# TRAFFIC TREND
# -----------------------------

st.header("Traffic Trend")

trend = current_df.groupby("date").agg({
    "clicks":"sum",
    "impressions":"sum"
})

st.line_chart(trend)

# -----------------------------
# TRAFFIC LOSS VS PREVIOUS MONTH
# -----------------------------

st.header("📉 Traffic Loss vs Previous Month")

if prev_df.empty:

    st.info("Previous month data not available")

else:

    current_grouped = current_df.groupby(
        ["keyword","page"], as_index=False
    ).agg({
        "clicks":"sum",
        "impressions":"sum",
        "ctr":"mean",
        "position":"mean"
    })

    prev_grouped = prev_df.groupby(
        ["keyword","page"], as_index=False
    ).agg({
        "clicks":"sum",
        "impressions":"sum",
        "ctr":"mean",
        "position":"mean"
    })

    loss_df = pd.merge(
        current_grouped,
        prev_grouped,
        on=["keyword","page"],
        how="outer",
        suffixes=("_current","_prev")
    )

    loss_df = loss_df.fillna(0)

    loss_df["click_loss"] = loss_df["clicks_prev"] - loss_df["clicks_current"]
    loss_df["impression_change"] = loss_df["impressions_current"] - loss_df["impressions_prev"]
    loss_df["ctr_change"] = loss_df["ctr_current"] - loss_df["ctr_prev"]
    loss_df["rank_change"] = loss_df["position_current"] - loss_df["position_prev"]

    loss_df = loss_df.sort_values("click_loss", ascending=False)

    display_cols = [
        "keyword",
        "page",
        "clicks_prev",
        "clicks_current",
        "click_loss",
        "impressions_prev",
        "impressions_current",
        "impression_change",
        "ctr_prev",
        "ctr_current",
        "ctr_change",
        "position_prev",
        "position_current",
        "rank_change"
    ]

    st.dataframe(loss_df[display_cols].head(100))

# -----------------------------
# NEW KEYWORDS
# -----------------------------

st.header("New Keywords")

if not prev_df.empty:

    new_kw = set(current_df["keyword"]) - set(prev_df["keyword"])

    new_kw_df = current_df[current_df["keyword"].isin(new_kw)]

    new_kw_table = new_kw_df.groupby("keyword").agg({
        "clicks":"sum",
        "impressions":"sum",
        "position":"mean"
    }).sort_values("impressions",ascending=False).head(20)

    st.dataframe(new_kw_table)

# -----------------------------
# AGENT RECOMMENDATIONS
# -----------------------------

st.header("SEO Agent Recommendations")

recommendations = []

if not quick_kw.empty:
    recommendations.append("Improve ranking for keywords between position 8-20")

if not ctr_kw.empty:
    recommendations.append("Improve CTR for top ranking keywords")

if 'loss_df' in locals() and not loss_df.empty:
    recommendations.append("Investigate keywords losing traffic vs previous month")

if len(recommendations)==0:
    st.success("SEO performance stable")

for r in recommendations:
    st.write("•",r)
