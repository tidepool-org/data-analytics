import json
import os
import random
import time

from get_donor_data.get_single_donor_metadata import get_shared_metadata
from get_donor_data.get_single_tidepool_dataset import get_data
from anonymize_and_export_data.anonymize_and_export import full_anon_pipeline_2025
from estimate_local_time.estimate_local_time import run_estimate_local_time


def load_user_group2_nonAID():
    """
    Primary group of interest. Return dict with userid mapped to qualifying months.
    """
    rgroup2_nonAID_users = json.load(open(
        "/Users/csummers/dev/data-science-tidepool-api-python/data_science_tidepool_api_python/projects/tbddp/r_UserCategoryA_final_nonAID.json"))
    rgroup2_nonAID_users_qual = {user_id: months for user_id, months in rgroup2_nonAID_users.items() if
                                      len(months) > 0}

    return rgroup2_nonAID_users_qual


def load_user_group2_AID():
    """
    Secondary group of interest. Return dict with userid mapped to qualifying months.
    """
    rgroup2_AID_users = json.load(open(
        "/Users/csummers/dev/data-science-tidepool-api-python/data_science_tidepool_api_python/projects/tbddp/r_UserCategoryA_final_AID.json"))
    rgroup2_AID_users_qual = {user_id: months for user_id, months in rgroup2_AID_users.items() if
                                      len(months) > 0}

    return rgroup2_AID_users_qual


def load_user_group1():
    """
    Tertiary group of interest. Return dict with userid mapped to qualifying months.
    """
    rgroup1_users = json.load(open("/Users/csummers/dev/data-science-tidepool-api-python/data_science_tidepool_api_python/projects/tbddp/rgroup1_final.json"))
    rgroup1_users_qual = {user_id: months for user_id, months in rgroup1_users.items() if
                                      len(months) > 0}

    return rgroup1_users_qual


def load_r_q2_2025_delivered_user_group():
    """
    user group delivered R. Q2 2025
    """
    rgroup_delivered = json.load(open("./final_plus_suppl_tp_userids.json"))
    return rgroup_delivered


def export_user(user_qual_id, qual_months, export_dirpath, weeks_of_data=624):
    """
    Process a single user start to finish
    """

    user_start_time = time.time()

    metadata_df, _ = get_shared_metadata(userid_of_shared_user=user_qual_id)
    data, _ = get_data(userid_of_shared_user=user_qual_id, weeks_of_data=weeks_of_data)

    data = run_estimate_local_time(data)

    full_anon_pipeline_2025(data, metadata_df, qual_months, user_qual_id, export_dirpath)

    user_total_time = int(time.time() - user_start_time)

    print(f"\n\n\tUser time {user_total_time} seconds.")


def export_all_users(users_qualified_dict, export_dirpath):
    """
    Full process of collecting and anonymizing data for a group of users
    """
    process_start_time = time.time()

    time_str = time.strftime("%Y-%m-%d_%H-%M-%S")

    rand_state = random.Random(12345678)
    user_qual_ids = list(users_qualified_dict.keys())
    rand_state.shuffle(user_qual_ids)

    failed_users = dict()

    for i, user_qual_id in enumerate(user_qual_ids, 1):

        qual_months = users_qualified_dict[user_qual_id]

        try:
            print(f"Starting user {i}")
            weeks_of_data=33 # refresh Feb to Oct
            export_user(user_qual_id, qual_months, export_dirpath, weeks_of_data=weeks_of_data)
            print(f"Success user {i}")
        except Exception as e:
            failed_users[user_qual_id] = str(e)
            print(f"FAILED user {i}. Error {str(e)}")
            json.dump(failed_users, open(f"failed_users_{time_str}.json", "w"))

        process_total_time = int(time.time() - process_start_time)
        print(f"Total Time {process_total_time}. Num failed {len(failed_users)}. Num processed {i}\n")

        if i == 25:  # testing
            break


if __name__ == "__main__":

    users_to_export = load_user_group2_nonAID()
    # export_dirpath = "./data/rgroup2_nonAID/"

    # users_to_export = load_user_group2_AID()
    # export_dirpath = "./data/rgroup2_AID/"

    # users_to_export = load_user_group1()
    # export_dirpath = "./data/rgroup1/"

    # failed_users = json.load(open("failed_users.json"))
    # export_dirpath = "./data/rgroup2_failed_users/"

    users_to_export = load_r_q2_2025_delivered_user_group()
    export_dirpath = "./data/rgroup_delivered_Nov2025_refresh"

    # users_to_export = {user: months for user, months in users_to_export.items() if user == ""}
    # users_to_export = {user: months for user, months in users_to_export.items() if user in failed_users}

    export_all_users(users_to_export, export_dirpath)