import streamlit as st
import pandas as pd
import json
from datetime import datetime
import io

st.set_page_config(page_title="Matches", layout="wide")
@st.cache_data
def load_data():
    return pd.read_csv("device_match_humanrating.csv")

data = load_data()


if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'welcome'
    st.session_state.current_index = 0
    st.session_state.ratings = {}
    st.session_state.completed = False
    st.session_state.filtered_indices = []
    st.session_state.id_start = 0
    st.session_state.id_end = 0
    st.session_state.range_selected = False
    st.session_state.initialized = False

def rate_match(rating):
    idx = st.session_state.filtered_indices[st.session_state.current_index]
    st.session_state.ratings[idx] = rating
    if st.session_state.current_index < len(st.session_state.filtered_indices) - 1:
        st.session_state.current_index += 1
        st.rerun()  
    else:
        st.session_state.completed = True
        st.rerun()  

def reset_session():
    st.session_state.view_mode = 'welcome'
    st.session_state.range_selected = False
    st.session_state.initialized = False
    st.session_state.current_index = 0
    st.session_state.ratings = {}
    st.session_state.completed = False
    st.session_state.filtered_indices = []
    st.session_state.id_start = 0
    st.session_state.id_end = 0
    st.rerun()

def generate_progress_json():
    progress_data = {
        "id_start": st.session_state.id_start,
        "id_end": st.session_state.id_end,
        "data_file_name": "device_match_humanrating.csv",
        "filtered_indices": st.session_state.filtered_indices,
        "current_index_in_filtered": st.session_state.current_index,
        "ratings": {str(k): v for k, v in st.session_state.ratings.items()},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return json.dumps(progress_data, indent=4)

def load_progress_from_upload(uploaded_file):
    try:
        progress_data = json.load(uploaded_file)
        required_keys = ["id_start", "id_end", "filtered_indices", "current_index_in_filtered", "ratings"]
        if not all(key in progress_data for key in required_keys):
            st.error("Invalid progress file format. Missing required data.")
            return False
        if "data_file_name" in progress_data and progress_data["data_file_name"] != "device_match_humanrating.csv":
            st.warning("This progress file was created for a different data file. Some IDs may not match.")
        st.session_state.id_start = progress_data["id_start"]
        st.session_state.id_end = progress_data["id_end"]
        st.session_state.filtered_indices = progress_data["filtered_indices"]
        st.session_state.current_index = progress_data["current_index_in_filtered"]
        st.session_state.ratings = {int(k): v for k, v in progress_data["ratings"].items() if v is not None}
        all_rated = all(idx in st.session_state.ratings for idx in st.session_state.filtered_indices)
        st.session_state.completed = all_rated
        st.session_state.range_selected = True
        st.session_state.initialized = True
        st.session_state.view_mode = 'rating'
        
        return True
    except Exception as e:
        st.error(f"Error loading progress file: {str(e)}")
        return False

def generate_rated_csv():
    results = data.copy()
    for idx, rating in st.session_state.ratings.items():
        if rating is not None:
            results.loc[idx, 'human'] = rating
    filtered_results = results[(results['id'] >= st.session_state.id_start) & 
                              (results['id'] <= st.session_state.id_end)]
    csv_buffer = io.StringIO()
    filtered_results.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    return csv_buffer.getvalue()

if st.session_state.view_mode == 'welcome':
    st.title("Matches")
    tab1, tab2 = st.tabs(["Start New Rating Session", "Load Progress from File"])
    with tab1:
        with st.form("id_range_form"):
            col1, col2 = st.columns(2)
            with col1:
                min_id = int(data['id'].min())
                max_id = int(data['id'].max())
                id_start = st.number_input("Start ID", min_value=min_id, max_value=max_id, value=min_id)            
            with col2:
                id_end = st.number_input("End ID", min_value=min_id, max_value=max_id, value=min_id)            
            submitted = st.form_submit_button("Start Rating")
            if submitted:
                if id_start > id_end:
                    st.error("Start ID must be less than or equal to End ID")
                else:
                    filtered_data = data[(data['id'] >= id_start) & (data['id'] <= id_end)]
                    if len(filtered_data) == 0:
                        st.error("No rows found in the selected ID range")
                    else:
                        st.session_state.filtered_indices = filtered_data.index.tolist()
                        st.session_state.id_start = id_start
                        st.session_state.id_end = id_end
                        st.session_state.range_selected = True
                        st.session_state.initialized = True
                        st.session_state.ratings = {idx: None for idx in st.session_state.filtered_indices}
                        st.session_state.current_index = 0
                        st.session_state.view_mode = 'rating'
                        st.rerun()
    with tab2:
        uploaded_file = st.file_uploader("Upload your progress file", type=["json"])
        if uploaded_file is not None:
            if load_progress_from_upload(uploaded_file):
                st.success("Progress loaded successfully!")
                st.rerun()

elif st.session_state.view_mode == 'rating':
    if len(st.session_state.filtered_indices) > 0:
        current_filtered_index = st.session_state.filtered_indices[st.session_state.current_index]
    else:
        st.error("No rows found in the selected ID range")
        reset_session()
    st.title("Matches")
    st.write(f"Rating items in ID range: {st.session_state.id_start} - {st.session_state.id_end}")
    filtered_len = len(st.session_state.filtered_indices)
    st.write(f"Current Item: {st.session_state.current_index + 1}/{filtered_len}")
    st.download_button(
        label="Save Progress (Download)",
        data=generate_progress_json(),
        file_name=f"rating_progress_IDs_{st.session_state.id_start}-{st.session_state.id_end}.json",
        mime="application/json",
        help="Download your current progress to continue later"
    )
    if st.session_state.completed:
        st.success("All items in your range have been rated!")
        results = data.copy()
        for idx, rating in st.session_state.ratings.items():
            if rating is not None:
                results.loc[idx, 'human'] = rating
        filtered_results = results[(results['id'] >= st.session_state.id_start) & (results['id'] <= st.session_state.id_end)]
        st.write("### Results")
        st.dataframe(filtered_results)

        st.download_button(
            label="Download Rated Rows (CSV)",
            data=generate_rated_csv(),
            file_name=f"device_match_ratings_IDs_{st.session_state.id_start}-{st.session_state.id_end}.csv",
            mime="text/csv",
            help="Download your ratings for this ID range"
        )
        if st.button("Rate Another Range"):
            reset_session()
    else:
        current_row = data.iloc[current_filtered_index]
        col_left, col_right, col_buttons = st.columns([5, 5, 2])
        
        with col_left:
            st.subheader("OPD Device")
            st.write(current_row['opd_device'])
            st.write("Company: " + current_row['opd_company'])
            st.write(f"ID: {current_row['id']}") 
        
        with col_right:
            st.subheader("FDA Device")
            st.write(current_row['fda_device'])
            st.write("Company: " + current_row['fda_company'])
        with col_buttons:
            st.write("")  
            st.write("")  
            if st.button("Match", key="match_btn", use_container_width=True):
                rate_match(1)
            
            if st.button("No Match", key="no_match_btn", use_container_width=True):
                rate_match(0)
                
            if st.button("Skip", key="skip_btn", use_container_width=True):
                if st.session_state.current_index < len(st.session_state.filtered_indices) - 1:
                    st.session_state.current_index += 1
                    st.rerun()  
                else:
                    st.session_state.completed = True
                    st.rerun()  
        st.write("") 
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("Previous", disabled=st.session_state.current_index == 0, use_container_width=True):
                st.session_state.current_index -= 1
                st.rerun()  
        with col_next:
            if st.button("Next", disabled=st.session_state.current_index == len(st.session_state.filtered_indices) - 1, use_container_width=True):
                st.session_state.current_index += 1
                st.rerun()  

elif st.session_state.view_mode == 'range_completed':
    st.title("Rating Task Completed")
    st.success(f"Great job! Your ratings for ID range {st.session_state.id_start}-{st.session_state.id_end} have been saved.")
    st.download_button(
        label="Download Rated Rows (CSV)",
        data=generate_rated_csv(),
        file_name=f"device_match_ratings_IDs_{st.session_state.id_start}-{st.session_state.id_end}.csv",
        mime="text/csv",
        help="Download your ratings for this ID range"
    )
    if st.button("Start Another Rating Task", use_container_width=True):
        reset_session() 