# Future Health Risk Prediction

def predict_all_next_values_from_firestore(user_id):
    results = []
    test_results_ref = db.collection("users").document(user_id).collection("test_results")
    test_docs = test_results_ref.where("value", "!=", None).stream()

    all_tests = {}
    for doc in test_docs:
        data = doc.to_dict()
        test_name = data.get("test_name")
        value = data.get("value")
        date = data.get("date")
        try:
            if test_name and value is not None and date:
                val = float(value)
                date_obj = pd.to_datetime(date) if not isinstance(date, datetime) else date
                if test_name not in all_tests:
                    all_tests[test_name] = []
                all_tests[test_name].append((date_obj, val))
        except Exception:
            continue

    for test_name, records in all_tests.items():
        if len(records) < 2:
            results.append({
                "Test Name": test_name,
                "Message": "Insufficient historical data for prediction (need at least 2 data points)."
            })
            continue

        doc = db.collection("blood_tests").document(test_name).get()
        if not doc.exists:
            results.append({
                "Test Name": test_name,
                "Message": "Test not found in Firestore reference."
            })
            continue

        sorted_data = sorted(records, key=lambda x: x[0])
        dates_sorted, values_sorted = zip(*sorted_data)
        dates_sorted = pd.to_datetime(dates_sorted)
        values_sorted = list(values_sorted)

        days_since_first = (dates_sorted - dates_sorted[0]).days.values.reshape(-1, 1)
        model = LinearRegression()
        model.fit(days_since_first, values_sorted)

        last_date = dates_sorted[-1]
        predict_date = last_date + pd.Timedelta(days=30)
        days_to_predict = (predict_date - dates_sorted[0]).days
        predicted_value = float(model.predict([[days_to_predict]])[0])

        results.append({
            "Test Name": test_name,
            "Predicted Value (Next 30 Days)": round(predicted_value, 2),
            "Prediction Date": predict_date.strftime('%Y-%m-%d')
        })

    return results