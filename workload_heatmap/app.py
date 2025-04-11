import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.heatmap import (
    load_data, 
    calculate_workload, 
    identify_overloaded_users, 
    suggest_task_reallocation
)

st.set_page_config(
    page_title="Task Management - Workload Heatmap",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Workload Heatmap")
st.markdown("### Identify overburdened team members and balance workload")

@st.cache_data
def get_data():
    return load_data()

users_df, tasks_df, time_logs_df, dependencies_df, notifications_df = get_data()

workload_df = calculate_workload(users_df, tasks_df, time_logs_df)

st.sidebar.title("Heatmap Settings")
threshold_percentile = st.sidebar.slider(
    "Overload Threshold (Percentile)",
    min_value=50,
    max_value=95,
    value=75,
    step=5,
    help="Users with workload above this percentile are considered overloaded"
)

overloaded_users, threshold = identify_overloaded_users(workload_df, threshold_percentile)

tab1, tab2, tab3 = st.tabs(["Workload Heatmap", "Overloaded Users", "Task Reallocation"])

with tab1:
    st.subheader("Team Workload Distribution")

    active_users = workload_df[workload_df['tasks_assigned'] > 0].copy()
    active_users.sort_values('workload_score', ascending=False, inplace=True)

    fig = px.bar(
        active_users,
        x="name",
        y="workload_score",
        color="workload_score",
        color_continuous_scale="RdYlGn_r",
        hover_data=["pending_tasks", "tasks_assigned", "total_time_spent"],
        height=500,
    )

    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=len(active_users)-0.5,
        y0=threshold,
        y1=threshold,
        line=dict(color="red", width=2, dash="dash"),
    )

    fig.add_annotation(
        x=len(active_users)-1,
        y=threshold * 1.05,
        text=f"Overload Threshold ({threshold_percentile}th percentile)",
        showarrow=False,
        font=dict(color="red")
    )

    fig.update_layout(
        xaxis_title="Team Members",
        yaxis_title="Workload Score",
        xaxis={'categoryorder':'total descending'}
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Workload Details")

    display_df = workload_df.copy()
    display_df = display_df[display_df['tasks_assigned'] > 0].sort_values('workload_score', ascending=False)
    display_df = display_df[['name', 'tasks_assigned', 'pending_tasks', 'total_time_spent', 'workload_score']]
    display_df.rename(columns={
        'name': 'Team Member',
        'tasks_assigned': 'Total Tasks',
        'pending_tasks': 'Pending Tasks',
        'total_time_spent': 'Time Spent (mins)',
        'workload_score': 'Workload Score'
    }, inplace=True)

    def highlight_overloaded(s):
        is_overloaded = s['Workload Score'] > threshold
        return ['background-color: #ffcccc' if is_overloaded else '' for _ in s]

    st.dataframe(
        display_df.style.apply(highlight_overloaded, axis=1),
        use_container_width=True,
        height=400
    )

with tab2:
    st.subheader("Overloaded Team Members")

    if len(overloaded_users) > 0:
        st.info(f"Found {len(overloaded_users)} team members with high workload (above {threshold_percentile}th percentile)")

        col1, col2 = st.columns(2)

        for i, (_, user) in enumerate(overloaded_users.iterrows()):
            with col1 if i % 2 == 0 else col2:
                with st.expander(f"{user['name']} (Workload: {user['workload_score']:.2f})"):
                    user_tasks = tasks_df[tasks_df['assigned_user_id'] == user['user_id']].copy()
                    user_tasks['due_date'] = pd.to_datetime(user_tasks['due_date'])

                    st.markdown(f"**Assigned Tasks:** {int(user['tasks_assigned'])}")
                    st.markdown(f"**Pending Tasks:** {int(user['pending_tasks'])}")
                    st.markdown(f"**Total Time Logged:** {int(user['total_time_spent'])} minutes")

                    pending = user_tasks[user_tasks['status'] != 'Done'].sort_values('due_date')
                    if len(pending) > 0:
                        st.markdown("#### Pending Tasks:")
                        st.dataframe(
                            pending[['title', 'priority', 'due_date']].rename(
                                columns={'title': 'Task', 'priority': 'Priority', 'due_date': 'Due Date'}
                            ),
                            use_container_width=True
                        )
                    else:
                        st.markdown("No pending tasks found, but high historical workload.")
    else:
        st.success("No team members are currently overloaded based on the selected threshold.")

with tab3:
    st.subheader("Suggested Task Reallocation")

    if len(overloaded_users) > 0:
        suggestions = suggest_task_reallocation(overloaded_users, workload_df, tasks_df, dependencies_df, notifications_df)

        if len(suggestions) > 0:
            st.info(f"Found {len(suggestions)} tasks that could be reallocated to balance workload")

            for i, suggestion in enumerate(suggestions):
                with st.expander(f"Task: {suggestion['task_title']} (Priority: {suggestion['priority']})"):
                    st.markdown(f"**From:** {suggestion['from_user_name']} (Overloaded)")
                    st.markdown(f"**To:** {suggestion['to_user_name']} (Has capacity)")
                    st.markdown(f"**Due Date:** {suggestion['due_date']}")

                    if st.button(f"Reassign Task", key=f"reassign_{i}"):
                        st.success(f"Task would be reassigned from {suggestion['from_user_name']} to {suggestion['to_user_name']}")
        else:
            st.warning("No suitable task reallocation suggestions found.")
    else:
        st.success("No reallocation needed as no team members are currently overloaded.")

st.markdown("---")
st.caption("Workload Heatmap | Task Management System | v1.0")
