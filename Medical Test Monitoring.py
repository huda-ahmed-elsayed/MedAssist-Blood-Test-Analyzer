# Monitoring

def analyze_trend_from_firestore(user_id):
    """
    Analyzes trends for all medical tests by comparing the latest value to previous historical values.

    Parameters:
    - user_id: str - ID of the user.

    Returns:
    - List of dicts with trend status, past values (if any), and monitoring priority (if applicable).
    """
    results = []

    test_results_ref = db.collection("users").document(user_id).collection("test_results")
    test_docs = test_results_ref.where("value", "!=", None).stream()

    all_tests = {}
    for doc in test_docs:
        data = doc.to_dict()
        test_name = data.get("test_name")
        value = data.get("value")
        date = data.get("date")
        if test_name and value is not None and date:
            try:
                val = float(value)
                date_obj = pd.to_datetime(date) if not isinstance(date, datetime) else date
                all_tests.setdefault(test_name, []).append((date_obj, val))
            except:
                continue

    for test_name, records in all_tests.items():
        try:
            sorted_records = sorted(records, key=lambda x: x[0])
            latest_date, current_value = sorted_records[-1]

            # If there's no past data
            if len(sorted_records) < 2:
                results.append({
                    "Test Name": test_name,
                    "Current Value": current_value,
                    "Trend Status": "No Historical Data"
                })
                continue

            *past_records, _ = sorted_records
            past_values = [val for _, val in past_records]
            last_value = past_values[-1]

            doc = db.collection("blood_tests").document(test_name).get()
            if not doc.exists:
                continue
            test_info = doc.to_dict()
            min_range = test_info.get("min_range")
            max_range = test_info.get("max_range")
            if min_range is None or max_range is None:
                continue

            # Determine trend
            if current_value > last_value:
                trend_status = "Increasing (Possible Worsening)"
            elif current_value < last_value:
                trend_status = "Decreasing (Possible Improvement)"
            else:
                trend_status = "Stable (No Change)"

            if current_value < min_range:
                trend_status += " (Below Normal)"
            elif current_value > max_range:
                trend_status += " (Above Normal)"
            else:
                trend_status += " (Within Normal Range)"

            # Determine monitoring priority
            if current_value < min_range or current_value > max_range:
                if abs(current_value - last_value) > (0.2 * last_value):
                    priority = "Critical, monitor weekly"
                else:
                    priority = "Warning, monitor monthly"
            else:
                priority = "Stable, monitor every 3 months"

            results.append({
                "Test Name": test_name,
                "Current Value": current_value,
                "Past Values": past_values,
                "Trend Status": trend_status,
                "Monitoring Priority": priority
            })

        except:
            continue

    return results