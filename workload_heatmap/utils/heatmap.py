import pandas as pd
import numpy as np
from datetime import datetime

def load_data():
    """Load data from CSV files"""
    users_df = pd.read_csv('data/users.csv')
    tasks_df = pd.read_csv('data/tasks.csv')
    time_logs_df = pd.read_csv('data/time_logs.csv')
    dependencies_df = pd.read_csv('data/task_dependencies.csv')
    notifications_df = pd.read_csv('data/notifications.csv')

    return users_df, tasks_df, time_logs_df, dependencies_df, notifications_df

def calculate_workload(users_df, tasks_df, time_logs_df):
    """Calculate workload for each user based on assigned tasks and time spent"""
    user_task_counts = tasks_df.groupby('assigned_user_id').size().reset_index(name='tasks_assigned')
    user_time_spent = time_logs_df.groupby('user_id')['duration_minutes'].sum().reset_index()
    user_time_spent.rename(columns={'duration_minutes': 'total_time_spent'}, inplace=True)

    pending_tasks = tasks_df[tasks_df['status'] != 'Done']
    pending_task_counts = pending_tasks.groupby('assigned_user_id').size().reset_index(name='pending_tasks')

    workload_df = users_df[['user_id', 'name', 'role']].copy()
    workload_df = pd.merge(workload_df, user_task_counts, left_on='user_id', right_on='assigned_user_id', how='left')
    workload_df = pd.merge(workload_df, pending_task_counts, left_on='user_id', right_on='assigned_user_id', how='left')
    workload_df = pd.merge(workload_df, user_time_spent, on='user_id', how='left')

    workload_df['tasks_assigned'] = workload_df['tasks_assigned'].fillna(0)
    workload_df['pending_tasks'] = workload_df['pending_tasks'].fillna(0)
    workload_df['total_time_spent'] = workload_df['total_time_spent'].fillna(0)

    workload_df['workload_score'] = (
        workload_df['pending_tasks'] * 3 + 
        workload_df['tasks_assigned'] * 1 + 
        workload_df['total_time_spent'] / 60
    )

    return workload_df

def identify_overloaded_users(workload_df, threshold_percentile=75):
    threshold = workload_df['workload_score'].quantile(threshold_percentile/100)
    overloaded_users = workload_df[workload_df['workload_score'] > threshold].copy()
    return overloaded_users, threshold

def suggest_task_reallocation(overloaded_users, workload_df, tasks_df, dependencies_df, notifications_df):
    median_workload = workload_df['workload_score'].median()
    users_with_capacity = workload_df[
        (workload_df['workload_score'] < median_workload) & 
        (~workload_df['user_id'].isin(overloaded_users['user_id']))
    ].copy()
    users_with_capacity.sort_values('workload_score', inplace=True)

    suggestions = []

    for _, user in overloaded_users.iterrows():
        user_tasks = tasks_df[
            (tasks_df['assigned_user_id'] == user['user_id']) & 
            (tasks_df['status'] != 'Done')
        ].copy()

        user_tasks['due_date'] = pd.to_datetime(user_tasks['due_date'])
        user_tasks.sort_values(['priority', 'due_date'], ascending=[False, True], inplace=True)

        for _, task in user_tasks.iterrows():
            
            dependent_tasks = dependencies_df[dependencies_df['task_id'] == task['task_id']]
            if not dependent_tasks.empty:
                incomplete_deps = dependent_tasks.merge(
                    tasks_df[['task_id', 'status']], 
                    left_on='depends_on_task_id', 
                    right_on='task_id'
                )
                if any(incomplete_deps['status'] != 'Done'):
                    continue

            recent_reminder = notifications_df[
                (notifications_df['user_id'] == user['user_id']) &
                (notifications_df['task_id'] == task['task_id']) &
                (notifications_df['type'] == 'reminder')
            ]
            if not recent_reminder.empty:
                continue

            if len(users_with_capacity) > 0:
                target_user = users_with_capacity.iloc[0]

                suggestions.append({
                    'task_id': task['task_id'],
                    'task_title': task['title'],
                    'from_user_id': user['user_id'],
                    'from_user_name': user['name'],
                    'to_user_id': target_user['user_id'],
                    'to_user_name': target_user['name'],
                    'priority': task['priority'],
                    'due_date': task['due_date']
                })

                users_with_capacity = pd.concat([users_with_capacity.iloc[1:], users_with_capacity.iloc[0:1]])
                break

    return suggestions
