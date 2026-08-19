
from pathlib import Path
import json
import math

import joblib
import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# DUBAI PROPERTY VALUE ESTIMATOR
# Single-page broker-facing application
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"

MODEL_FILE = MODEL_DIR / "valuation_model.joblib"
CATEGORIES_FILE = MODEL_DIR / "model_categories.json"
AREA_REFERENCE_FILE = MODEL_DIR / "area_reference.csv"
PROJECT_REFERENCE_FILE = MODEL_DIR / "project_reference.csv"


st.set_page_config(
    page_title="Dubai Property Value Estimator",
    page_icon="🏠",
    layout="wide",
)


# ============================================================
# SIMPLE STYLING
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .title {
        font-size: 2.3rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
    }

    .subtitle {
        color: #666;
        font-size: 1rem;
        margin-bottom: 1.6rem;
    }

    .estimate-label {
        color: #666;
        font-size: 1rem;
    }

    .estimate-value {
        font-size: 2.5rem;
        font-weight: 750;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD VALUATION ENGINE
# ============================================================

@st.cache_resource
def load_model():
    return joblib.load(MODEL_FILE)


@st.cache_data
def load_categories():
    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_references():
    area_ref = pd.read_csv(AREA_REFERENCE_FILE)
    project_ref = pd.read_csv(PROJECT_REFERENCE_FILE)

    for frame in (area_ref, project_ref):
        for column in frame.columns:
            if column not in {
                "AREA_EN",
                "PROJECT_EN",
                "last_area_date",
                "last_project_date",
            }:
                frame[column] = pd.to_numeric(
                    frame[column],
                    errors="coerce",
                )

    return area_ref, project_ref


required_files = [
    MODEL_FILE,
    CATEGORIES_FILE,
    AREA_REFERENCE_FILE,
    PROJECT_REFERENCE_FILE,
]

missing_files = [
    str(file_path)
    for file_path in required_files
    if not file_path.exists()
]

if missing_files:
    st.error("The valuation engine is missing required files.")
    for file_path in missing_files:
        st.write(file_path)
    st.stop()


try:
    model = load_model()
    categories = load_categories()
    area_reference, project_reference = load_references()
except Exception as exc:
    st.error(f"Could not load the valuation engine: {exc}")
    st.stop()


AREA_CATEGORIES = categories["area_categories"]
PROJECT_CATEGORIES = categories["project_categories"]


# ============================================================
# HELPERS
# ============================================================

def money(value):
    if value is None or pd.isna(value):
        return "—"

    number = float(value)

    if number >= 1_000_000:
        return f"AED {number / 1_000_000:.2f}M"

    return f"AED {number:,.0f}"


def parse_bedrooms(property_type):
    text = str(property_type).lower()

    if "studio" in text:
        return 0

    digits = "".join(
        character
        for character in text
        if character.isdigit()
    )

    return int(digits) if digits else 0


def get_latest_area_reference(area):
    rows = area_reference[
        area_reference["AREA_EN"].astype(str) == str(area)
    ].copy()

    if rows.empty:
        return None

    return rows.sort_values("last_area_date").iloc[-1]


def get_latest_project_reference(project):
    rows = project_reference[
        project_reference["PROJECT_EN"].astype(str) == str(project)
    ].copy()

    if rows.empty:
        return None

    return rows.sort_values("last_project_date").iloc[-1]


def build_features(
    area,
    project,
    property_type,
    area_sqft,
    parking,
    is_offplan,
    is_freehold,
):
    area_row = get_latest_area_reference(area)
    project_row = get_latest_project_reference(project)

    area_median = np.nan
    log_area_count = np.nan

    if area_row is not None:
        area_median = area_row.get(
            "area_90d_median_ppsf",
            np.nan,
        )
        log_area_count = area_row.get(
            "log_area_90d_count",
            np.nan,
        )

    project_median = np.nan
    log_project_count = np.nan
    project_history_available = 0

    if project_row is not None:
        project_median = project_row.get(
            "project_90d_median_ppsf",
            np.nan,
        )
        log_project_count = project_row.get(
            "log_project_90d_count",
            np.nan,
        )
        project_history_available = project_row.get(
            "project_history_available",
            1,
        )

        if pd.isna(project_history_available):
            project_history_available = 1

    features = pd.DataFrame(
        {
            "log_area_sqft": [math.log(float(area_sqft))],
            "bedrooms": [parse_bedrooms(property_type)],
            "parking_count": [int(parking)],
            "is_offplan": [int(is_offplan)],
            "is_freehold": [int(is_freehold)],
            "area_90d_median_ppsf": [area_median],
            "project_90d_median_ppsf": [project_median],
            "log_area_90d_count": [log_area_count],
            "log_project_90d_count": [log_project_count],
            "project_history_available": [
                int(project_history_available)
            ],
            "AREA_EN": [area],
            "PROJECT_EN": [project],
        }
    )

    # Exact pandas categorical representation used during training.
    features["AREA_EN"] = pd.Categorical(
        features["AREA_EN"],
        categories=AREA_CATEGORIES,
    )

    features["PROJECT_EN"] = pd.Categorical(
        features["PROJECT_EN"],
        categories=PROJECT_CATEGORIES,
    )

    return features, area_row, project_row


def estimate_market_value(features):
    predicted_log_value = model.predict(features)
    predicted_log_value = float(
        np.asarray(predicted_log_value).reshape(-1)[0]
    )

    # Model target was log_price.
    return float(np.exp(predicted_log_value))


# ============================================================
# PAGE
# ============================================================

st.markdown(
    '<div class="title">🏠 Dubai Property Value Estimator</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Enter the property details and get an estimated market value.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# PROPERTY INPUT
# ============================================================

st.markdown("### Property details")

left_column, right_column = st.columns(2)

with left_column:
    area = st.selectbox(
        "Area",
        AREA_CATEGORIES,
    )

    project = st.selectbox(
        "Project",
        PROJECT_CATEGORIES,
    )

    property_type = st.selectbox(
        "Property type",
        [
            "Studio",
            "1 B/R",
            "2 B/R",
            "3 B/R",
            "4 B/R",
            "5 B/R",
            "6 B/R",
        ],
    )


with right_column:
    area_sqft = st.number_input(
        "Property size (sq ft)",
        min_value=100,
        max_value=100000,
        value=800,
        step=50,
    )

    parking = st.number_input(
        "Parking spaces",
        min_value=0,
        max_value=10,
        value=1,
        step=1,
    )

    status = st.selectbox(
        "Property status",
        [
            "Off-Plan",
            "Ready",
        ],
    )

    freehold = st.checkbox(
        "Freehold",
        value=True,
    )


asking_price = st.number_input(
    "Asking price (optional)",
    min_value=0,
    value=0,
    step=10000,
)


# ============================================================
# ESTIMATE
# ============================================================

st.divider()

estimate_clicked = st.button(
    "ESTIMATE MARKET VALUE",
    type="primary",
    use_container_width=True,
)

if estimate_clicked:
    try:
        features, area_row, project_row = build_features(
            area=area,
            project=project,
            property_type=property_type,
            area_sqft=area_sqft,
            parking=parking,
            is_offplan=(status == "Off-Plan"),
            is_freehold=freehold,
        )

        estimated_value = estimate_market_value(features)
        estimated_ppsf = estimated_value / float(area_sqft)

        st.divider()

        st.markdown("### Estimated market value")

        result_left, result_right = st.columns(2)

        with result_left:
            st.markdown(
                '<div class="estimate-label">'
                'Estimated value'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="estimate-value">'
                f'{money(estimated_value)}'
                f'</div>',
                unsafe_allow_html=True,
            )

        with result_right:
            st.markdown(
                '<div class="estimate-label">'
                'Estimated value per sq ft'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="estimate-value">'
                f'AED {estimated_ppsf:,.0f}'
                f'</div>',
                unsafe_allow_html=True,
            )

        if asking_price > 0:
            difference = (
                estimated_value
                - float(asking_price)
            )

            difference_pct = (
                difference
                / float(asking_price)
                * 100
            )

            st.divider()
            st.markdown("### Asking price comparison")

            price_one, price_two, price_three = st.columns(3)

            price_one.metric(
                "Asking price",
                money(asking_price),
            )

            price_two.metric(
                "Estimated value",
                money(estimated_value),
            )

            price_three.metric(
                "Difference",
                money(difference),
            )

            if difference > 0:
                st.success(
                    f"The asking price is approximately "
                    f"{abs(difference_pct):.1f}% below the estimated value."
                )
            elif difference < 0:
                st.warning(
                    f"The asking price is approximately "
                    f"{abs(difference_pct):.1f}% above the estimated value."
                )
            else:
                st.info(
                    "The asking price is approximately equal to "
                    "the estimated value."
                )

        if area_row is None:
            st.info(
                "No recent area reference was found. "
                "The valuation model handled the missing history automatically."
            )

        if project_row is None:
            st.info(
                "No recent project reference was found. "
                "The valuation model handled the missing history automatically."
            )

    except Exception as exc:
        st.error("Could not calculate the estimate.")
        st.exception(exc)


st.divider()

st.caption(
    "Estimated market value is a model estimate, not a guaranteed sale price."
)
