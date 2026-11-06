import ast
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="IMDb Top 250 Movie Dashboard", page_icon="🎬", layout="wide")

DATA_FILE = Path(__file__).with_name("ToP 250 movies on imdb in 2026.csv")

st.title("🎬 IMDb Top 250 Movies — Interactive Dashboard")
st.caption("Explore movie ratings, genres, votes, worldwide gross, and movie details.")


def as_list(value):
    """Normalize CSV list fields whether they contain Python-list text or plain text."""
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, (list, tuple)):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [str(parsed).strip()] if str(parsed).strip() else []
    except (ValueError, SyntaxError):
        return [str(value).strip()] if str(value).strip() else []


@st.cache_data
def load_data(path):
    data = pd.read_csv(path)
    for column in ("genres", "countriesOfOrigin"):
        if column in data.columns:
            data[column] = data[column].apply(as_list)
    for column in ("averageRating", "numVotes", "grossWorldwide"):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


try:
    df = load_data(str(DATA_FILE))
except FileNotFoundError:
    st.error(f"Dataset not found: {DATA_FILE.name}. Place the CSV beside app.py.")
    st.stop()
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.stop()

st.success(f"Dataset loaded successfully: {len(df):,} movies.")

# SIDEBAR
st.sidebar.title("🎬 Movie Dashboard")

st.sidebar.write("Welcome to the Movie Analytics Dashboard!")

st.sidebar.divider()

st.sidebar.subheader("About the Dashboard")

st.sidebar.write("""
This dashboard helps you explore IMDb movie data.

You can:
- View movie statistics
- Explore different genres
- Analyse IMDb ratings
- Compare ratings and votes
- Find top-grossing movies
""")

st.sidebar.divider()

st.sidebar.info("Created as a Midsem Project")

# Section A: dataset loading and initial exploration
with st.expander("Dataset loading and initial exploration"):
    st.subheader("First 10 records")
    st.dataframe(df.head(10), use_container_width=True)
    info_left, info_right = st.columns(2)
    info_left.metric("Rows", df.shape[0])
    info_right.metric("Columns", df.shape[1])
    st.write("**Column names**", df.columns.tolist())
    st.write("**Data types**")
    st.dataframe(df.dtypes.astype(str).rename("Data type"), use_container_width=True)
    st.write("**Missing values by column**")
    st.dataframe(df.isna().sum().rename("Missing values"), use_container_width=True)

# Section B: KPI metrics
st.header("Movie Analytics Dashboard")
st.subheader("Key performance indicators")
mean_rating = df["averageRating"].mean() if "averageRating" in df else float("nan")
max_rating = df["averageRating"].max() if "averageRating" in df else float("nan")
total_votes = df["numVotes"].sum() if "numVotes" in df else 0
kpis = st.columns(4)
kpis[0].metric("Total movies", f"{len(df):,}")
kpis[1].metric("Average IMDb rating", f"{mean_rating:.2f}" if pd.notna(mean_rating) else "N/A")
kpis[2].metric("Highest IMDb rating", f"{max_rating:.1f}" if pd.notna(max_rating) else "N/A")
kpis[3].metric("Total votes", f"{total_votes:,.0f}")
st.divider()

# Section B: visualizations in focused tabs
genre_tab, rating_tab, votes_tab, gross_tab = st.tabs(
    ["Genre analysis", "Rating analysis", "Rating vs. votes", "Worldwide gross"]
)
with genre_tab:
    if "genres" in df:
        genre_counts = df["genres"].explode().dropna().value_counts().rename_axis("Genre").reset_index(name="Movies")
        st.subheader("Number of movies by genre")
        if not genre_counts.empty:
            fig = px.bar(genre_counts, x="Genre", y="Movies", title="Movies by genre")
            fig.update_layout(xaxis_title="Genre", yaxis_title="Number of movies")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No genre data is available.")
with rating_tab:
    st.subheader("IMDb rating distribution")
    ratings = df["averageRating"].dropna()
    if not ratings.empty:
        fig = px.histogram(x=ratings, nbins=10, labels={"x": "IMDb rating", "y": "Number of movies"}, title="Distribution of IMDb ratings")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rating data is available.")
with votes_tab:
    st.subheader("IMDb rating vs. number of votes")
    plot_data = df.dropna(subset=["averageRating", "numVotes"])
    if not plot_data.empty:
        fig = px.scatter(plot_data, x="averageRating", y="numVotes", hover_name="primaryTitle" if "primaryTitle" in df else None,
                         labels={"averageRating": "IMDb rating", "numVotes": "Number of votes"}, title="Rating and votes")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rating and vote data is available.")
with gross_tab:
    st.subheader("Top 10 movies by worldwide gross")
    if "grossWorldwide" in df and "primaryTitle" in df:
        top_gross = df.dropna(subset=["grossWorldwide"]).nlargest(10, "grossWorldwide")
        if not top_gross.empty:
            fig = px.bar(top_gross.sort_values("grossWorldwide"), x="grossWorldwide", y="primaryTitle", orientation="h",
                         labels={"grossWorldwide": "Worldwide gross", "primaryTitle": "Movie"}, title="Top 10 worldwide gross collections")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(top_gross[["primaryTitle", "grossWorldwide"]].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No worldwide gross data is available.")
    else:
        st.info("The dataset does not contain movie titles and worldwide gross columns.")

with st.expander("About this dataset"):
    st.write(f"The dataset contains **{df.shape[0]:,} records** and **{df.shape[1]} columns**.")
    st.write("Available movie information includes titles, genres, countries of origin, release details, ratings, votes, and gross collections where provided.")
    st.caption("Columns: " + ", ".join(df.columns))
st.info("Use the Movie Explorer below to combine filters and sort the matching titles.")

# Section C: interactive explorer
st.divider()
st.header("Interactive Movie Explorer")

# Reset widget values through callback before widgets are instantiated.
def reset_explorer():
    for key, value in {
        "explorer_genre": "All genres", "explorer_countries": [], "explorer_rating": (0.0, 10.0),
        "explorer_votes": 0, "explorer_search": "", "explorer_sort": "Descending",
    }.items():
        st.session_state[key] = value

available_genres = sorted({g for values in df.get("genres", pd.Series([[]] * len(df))) for g in values})
available_countries = sorted({c for values in df.get("countriesOfOrigin", pd.Series([[]] * len(df))) for c in values})
left, right = st.columns(2)
with left:
    st.selectbox("Genre", ["All genres"] + available_genres, key="explorer_genre")
    st.multiselect("Countries of origin", available_countries, key="explorer_countries")
    rating_values = df["averageRating"].dropna() if "averageRating" in df else pd.Series(dtype=float)
    lower, upper = (float(rating_values.min()), float(rating_values.max())) if not rating_values.empty else (0.0, 10.0)
    st.slider("IMDb rating range", min_value=lower, max_value=upper, value=(lower, upper), key="explorer_rating")
with right:
    st.number_input("Minimum number of votes", min_value=0, value=0, step=1000, key="explorer_votes")
    st.text_input("Search movie titles", key="explorer_search", placeholder="Type part of a title")
    st.radio("Sort IMDb ratings", ["Ascending", "Descending"], horizontal=True, key="explorer_sort")

filtered_df = df.copy()
if st.session_state.explorer_genre != "All genres":
    filtered_df = filtered_df[filtered_df["genres"].apply(lambda values: st.session_state.explorer_genre in values)]
if st.session_state.explorer_countries:
    selected_countries = set(st.session_state.explorer_countries)
    filtered_df = filtered_df[filtered_df["countriesOfOrigin"].apply(lambda values: bool(selected_countries.intersection(values)))]
min_rating, max_rating = st.session_state.explorer_rating
filtered_df = filtered_df[filtered_df["averageRating"].between(min_rating, max_rating, inclusive="both")]
filtered_df = filtered_df[filtered_df["numVotes"].fillna(0) >= st.session_state.explorer_votes]
if st.session_state.explorer_search.strip():
    filtered_df = filtered_df[filtered_df["primaryTitle"].str.contains(st.session_state.explorer_search.strip(), case=False, na=False)]
filtered_df = filtered_df.sort_values("averageRating", ascending=st.session_state.explorer_sort == "Ascending", na_position="last")
st.metric("Movies matching all filters", f"{len(filtered_df):,}")
st.dataframe(filtered_df, use_container_width=True, hide_index=True)
st.button("Reset filters", on_click=reset_explorer)

# Section C: form-based movie lookup and session state
st.divider()
st.header("Movie Search")
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "movie_search_message" not in st.session_state:
    st.session_state.movie_search_message = None

form_genres = ["Any genre"] + available_genres
with st.form("movie_search_form"):
    movie_query = st.text_input("Movie title")
    preferred_genre = st.selectbox("Preferred genre", form_genres)
    rating_floor = st.slider("Minimum IMDb rating", min_value=0.0, max_value=10.0, value=7.0, step=0.1)
    submitted = st.form_submit_button("Search movie")

if submitted:
    matches = df[df["primaryTitle"].str.contains(movie_query.strip(), case=False, na=False)] if movie_query.strip() else df.iloc[0:0]
    matches = matches[matches["averageRating"].fillna(0) >= rating_floor]
    if preferred_genre != "Any genre":
        matches = matches[matches["genres"].apply(lambda values: preferred_genre in values)]
    if not matches.empty:
        st.session_state.selected_movie = matches.sort_values("averageRating", ascending=False).iloc[0].to_dict()
        st.session_state.movie_search_message = "found"
    else:
        st.session_state.selected_movie = None
        st.session_state.movie_search_message = "not_found"

if st.session_state.movie_search_message == "found" and st.session_state.selected_movie:
    movie = st.session_state.selected_movie
    st.success("Matching movie found.")
    st.subheader(movie.get("primaryTitle", "Selected movie"))
    detail_cols = st.columns(4)
    detail_cols[0].write("**Genre**\n" + ", ".join(movie.get("genres") or []))
    detail_cols[1].metric("IMDb rating", f"{movie['averageRating']:.1f}" if pd.notna(movie.get("averageRating")) else "N/A")
    detail_cols[2].metric("Number of votes", f"{movie['numVotes']:,.0f}" if pd.notna(movie.get("numVotes")) else "N/A")
    detail_cols[3].write("**Countries**\n" + ", ".join(movie.get("countriesOfOrigin") or []))
elif st.session_state.movie_search_message == "not_found":
    st.info("No movie matched the submitted title, genre, and minimum rating. Try changing your preferences.")


# FOOTER
st.divider()

st.markdown(
    """
    <div style="text-align: center; padding: 15px;">
        <h4>🎬 Movie Analytics Dashboard</h4>
        <p>Midsem Project | Made by Shilpa</p>
        <p>Built using Python, Pandas and Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
