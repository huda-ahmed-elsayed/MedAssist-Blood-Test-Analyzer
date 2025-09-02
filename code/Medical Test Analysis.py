# AI-Powered Medical Test Analysis

def classify_test_result(test_name, test_value):
    """
    Classifies a test result and generates a plot.
    Now retrieves test reference data from Firestore.
    """

    # Step 1: Retrieve document from Firestore
    doc = db.collection("blood_tests").document(test_name).get()
    if not doc.exists:
        return {"Message": "Test not found in Firestore."}, None

    test_info = doc.to_dict()

    # Step 2: Safely extract and convert values
    try:
        test_value = float(test_value)
        min_range = float(test_info.get("min_range", None))
        max_range = float(test_info.get("max_range", None))
    except (ValueError, TypeError):
        return {"Message": "Invalid test or range values."}, None

    health_info = test_info.get("health_information", "No additional health information available.")

    # Step 3: Determine result and color
    if test_value < min_range:
        result = "Low"
        value_color = "red"
        indication = test_info.get("low_values_indicate", "Low values may indicate an issue.")
        recommendation = test_info.get("treatment_guide", "Consult a doctor for further evaluation.")
    elif test_value > max_range:
        result = "High"
        value_color = "red"
        indication = test_info.get("high_values_indicate", "High values may indicate an issue.")
        recommendation = test_info.get("treatment_guide", "Consult a doctor for further evaluation.")
    else:
        result = "Normal"
        value_color = "dodgerblue"
        indication = "Within healthy range."
        recommendation = "No treatment required."

    # Time-to-Normal Estimation
    time_to_normal = "Test result is within the normal range."
    if result in ["Low", "High"]:
        midpoint = (min_range + max_range) / 2
        deviation = abs(test_value - midpoint)
        normal_range_width = max_range - min_range
        daily_change_rate = 0.015 * normal_range_width

        if daily_change_rate > 0:
            estimated_days = int(deviation / daily_change_rate)
            estimated_days = max(estimated_days, 3)
            if estimated_days >= 30:
                months = estimated_days // 30
                days = estimated_days % 30
                time_text = f"{months} month{'s' if months > 1 else ''}" + (f" and {days} days" if days > 0 else "")
            else:
                time_text = f"{estimated_days} day{'s' if estimated_days > 1 else ''}"
            if result == "Low":
                time_to_normal = f"With proper management, levels may normalize in approximately {time_text}."
            else:
                time_to_normal = f"If the current trend continues, value may stabilize within {time_text}."
        else:
            time_to_normal = "Unable to estimate time-to-normal due to insufficient data."

    # Re-test recommendation
    if result == "Normal":
        re_test_recommendation = "No immediate concern, retest in 90 days."
    elif result in ["Low", "High"]:
        re_test_recommendation = "Trending poorly — retest in 14 days."
    else:
        re_test_recommendation = "Critical — immediate consultation advised."

    # Prepare result dictionary
    result_data = {
        "Test Name": test_name,
        "Result": result,
        "Possible Diseases": indication,
        "Treatment Guide": recommendation,
        "Doctor Specialization": (
            test_info.get("high_doctor_specialization_to_visit", "General Physician") if result == "High" else
            test_info.get("low_doctor_specialization_to_visit", "General Physician")
        ),
        "Time to Reach Normal Range": time_to_normal,
        "Next Recommended Test Date": re_test_recommendation,
        "Health Information": health_info
    }

    print(result_data)

    # Plotting
    buffer = (max_range - min_range) * 0.5 if max_range != min_range else abs(min_range) * 0.5
    x_min = min(min_range - buffer, test_value - buffer)
    x_max = max(max_range + buffer, test_value + buffer)

    plt.figure(figsize=(9, 5))
    if test_value < min_range:
        plt.axvspan(x_min, min_range, color='salmon', alpha=0.3, label='Below Normal Range')
    else:
        plt.axvspan(x_min, min_range, color='white', alpha=0.3)
    if test_value > max_range:
        plt.axvspan(max_range, x_max, color='salmon', alpha=0.3, label='Above Normal Range')
    else:
        plt.axvspan(max_range, x_max, color='white', alpha=0.3)
    plt.axvspan(min_range, max_range, color='skyblue', alpha=0.3, label='Normal Range')
    plt.axvline(min_range, color='dodgerblue', linestyle='--', label='Min Range', lw=2)
    plt.axvline(max_range, color='royalblue', linestyle='--', label='Max Range', lw=2)
    plt.scatter(test_value, 0, color=value_color, s=250, marker='o', edgecolors='black', label="Your Test Value")
    plt.annotate(f"Your value: {test_value}",
                 xy=(test_value, 0),
                 xytext=(test_value, 0.07),
                 fontsize=12,
                 color=value_color,
                 arrowprops=dict(facecolor=value_color, arrowstyle="->", lw=2))
    plt.xlim(x_min, x_max)
    plt.xlabel("Test Value", fontsize=13, color='black')
    plt.ylabel("Indicator", fontsize=13, color='black')
    plt.title(f"{test_name} Test Result", fontsize=15, color='black')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)

    # Save the plot
    plot_filename = f"{test_name.replace(' ', '_')}_test_result.png"
    os.makedirs("plots", exist_ok=True)
    plot_path = os.path.join("plots", plot_filename)
    plt.savefig(plot_path, bbox_inches='tight')
    plt.close()

    return result_data, plot_path



# Health Score Calculation

def calculate_risk_score(test_results):
    """
    Calculates a health risk score based on multiple test results using Firestore data
    and provides a user-friendly summary.

    Parameters:
    test_results (dict): A dictionary with test names as keys and test values as values.

    Returns:
    dict: A summary with total abnormal count, health score, health status, and user message.
    """
    total_score = 0
    max_possible_score = len(test_results) * 2
    abnormal_count = 0

    for test_name, test_value in test_results.items():
        # Convert test_value to float if possible
        try:
            test_value = float(test_value)
        except (ValueError, TypeError):
            continue  # Skip invalid test values

        # Retrieve document from Firestore
        doc = db.collection("blood_tests").document(test_name).get()
        if not doc.exists:
            continue  # Skip if test not found

        test_data = doc.to_dict()

        min_range = test_data.get("min_range", None)
        max_range = test_data.get("max_range", None)

        if min_range is None or max_range is None:
            continue  # Skip if range is not defined

        # Score calculation
        if test_value < min_range:
            total_score += 1
            abnormal_count += 1
        elif test_value > max_range:
            total_score += 2
            abnormal_count += 1
        else:
            total_score += 0

    # Risk and Health Score Calculation
    risk_score = (total_score / max_possible_score) * 100 if max_possible_score > 0 else 0
    health_score = round(100 - risk_score, 2)

    # Natural Language Summary
    if health_score >= 80:
        health_status = "Low Risk (Healthy)"
        message = f"Your health score is {health_score}%, indicating good health. Keep monitoring periodically."
    elif health_score >= 50:
        health_status = "Moderate Risk (Needs Attention)"
        message = f"Your health score is {health_score}%, which indicates you should follow up with your healthcare provider."
    else:
        health_status = "High Risk (Critical Condition)"
        message = f"Your health score is {health_score}%, indicating a critical health risk. Immediate medical attention is advised."

    return {
        "Total Abnormal Results": abnormal_count,
        "Health Score": f"{health_score}%",
        "Health Status": health_status,
        "Health Summary Message": message
    }




# Care Guide

def extract_unique_care_guides(test_results):
    """
    Extracts unique care guides from Firestore based on the test results.

    Parameters:
    test_results (dict): A dictionary with test names as keys and test values as values.

    Returns:
    list: A list of unique care guides.
    """
    unique_care_guides = set()

    for test_name in test_results.keys():
        # Retrieve test document from Firestore
        doc = db.collection("blood_tests").document(test_name).get()
        if doc.exists:
            data = doc.to_dict()
            care_guide = data.get("care_guide")
            if care_guide:  # Add only non-empty care guides
                unique_care_guides.add(care_guide)
        else:
            print(f"Warning: Test '{test_name}' not found in Firestore.")

    return list(unique_care_guides)




# Report for AI-Powered Medical Test Analysis

def generate_medical_report_from_firestore(user_id):
    """
    Fetches latest test results and user data from Firestore, classifies results,
    generates a PDF medical report, and returns the file path (URL) to the user.
    """

    # Get user info
    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found.")

    user_data = user_doc.to_dict()
    patient_name = user_data.get("username", "Unknown")
    patient_age = user_data.get("age", "N/A")

    # Fetch latest test result per test
    test_results_ref = db.collection("users").document(user_id).collection("test_results")
    test_docs = test_results_ref.where("value", "!=", None).stream()

    latest_tests = {}
    for doc in test_docs:
        data = doc.to_dict()
        test_name = data.get("test_name")
        value = data.get("value")
        date_value = data.get("date")

        # Ignore invalid or empty values
        if test_name and value not in [None, ""] and date_value:
            date_obj = date_value if isinstance(date_value, datetime) else datetime.strptime(str(date_value), "%Y-%m-%d")
            if (test_name not in latest_tests) or (date_obj > latest_tests[test_name]["date"]):
                latest_tests[test_name] = {
                    "value": value,
                    "date": date_obj
                }

    test_results = {name: entry["value"] for name, entry in latest_tests.items()}

    grouped_tests = [
        ('Lymphocytes', 'Lymphocytes %'),
        ('Monocytes', 'Monocytes %'),
        ('Neutrophils', 'Neutrophils %'),
        ('Eosinophils', 'Eosinophils %'),
        ('Basophils', 'Basophils %')
    ]

    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        report_filename = temp_pdf.name
        pdf = SimpleDocTemplate(report_filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Comprehensive Medical Test Report", styles['Title']))
        story.append(Spacer(1, 12))

        patient_details = [
            f"<b>Patient Name:</b> {patient_name}",
            f"<b>Age:</b> {patient_age}",
            f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}"
        ]
        for detail in patient_details:
            story.append(Paragraph(detail, styles['Normal']))
        story.append(Spacer(1, 12))

        abnormal_count = 0
        processed_tests = set()

        # Process grouped tests
        for group in grouped_tests:
            if all(test in test_results for test in group):
                group_results = []
                has_abnormal = False
                combined_info = {}
                last_result = None

                for test in group:
                    result, plot_filename = classify_test_result(test, test_results[test])
                    group_results.append((test, result, plot_filename))
                    processed_tests.add(test)
                    last_result = result
                    if result.get("Result") != "Normal":
                        has_abnormal = True
                        combined_info = result

                for test, result, plot_filename in group_results:
                    story.append(Paragraph(f"<b>Test:</b> {test}", styles['Normal']))
                    story.append(Paragraph(f"<b>Your Value:</b> {test_results[test]}", styles['Normal']))
                    story.append(Paragraph(f"<b>Result:</b> {result.get('Result', 'Unknown')}", styles['Normal']))

                    if plot_filename:
                        try:
                            story.append(Image(plot_filename, width=400, height=200))
                        except Exception:
                            story.append(Paragraph(f"<b>Plot Error:</b> Could not display plot for {test}.", styles['Normal']))
                    story.append(Spacer(1, 12))

                if has_abnormal:
                    story.append(Paragraph(f"<b>Possible Diseases:</b> {combined_info.get('Possible Diseases', 'N/A')}", styles['Normal']))
                    story.append(Paragraph(f"<b>Treatment Guide:</b> {combined_info.get('Treatment Guide', 'N/A')}", styles['Normal']))
                    story.append(Paragraph(f"<b>Suggested Doctor:</b> {combined_info.get('Doctor Specialization', 'N/A')}", styles['Normal']))
                    story.append(Paragraph(f"<b>Time to Reach Normal Range:</b> {combined_info.get('Time to Reach Normal Range', 'N/A')}", styles['Normal']))
                    abnormal_count += 1

                # Always show these regardless of result
                story.append(Paragraph(f"<b>Next Recommended Test Date:</b> {last_result.get('Next Recommended Test Date', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Health Information:</b> {last_result.get('Health Information', 'N/A')}", styles['Normal']))
                story.append(Spacer(1, 12))

        # Process remaining individual tests
        for test_name, test_value in test_results.items():
            if test_name in processed_tests:
                continue

            result, plot_filename = classify_test_result(test_name, test_value)
            story.append(Paragraph(f"<b>Test:</b> {test_name}", styles['Normal']))
            story.append(Paragraph(f"<b>Your Value:</b> {test_value}", styles['Normal']))

            if "Result" not in result:
                story.append(Paragraph(f"<b>Status:</b> Unable to analyze. Reason: {result.get('Message', 'Unknown error')}", styles['Normal']))
                story.append(Spacer(1, 12))
                continue

            story.append(Paragraph(f"<b>Result:</b> {result['Result']}", styles['Normal']))

            if result["Result"] != "Normal":
                story.append(Paragraph(f"<b>Possible Diseases:</b> {result.get('Possible Diseases', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Treatment Guide:</b> {result.get('Treatment Guide', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Suggested Doctor:</b> {result.get('Doctor Specialization', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Time to Reach Normal Range:</b> {result.get('Time to Reach Normal Range', 'N/A')}", styles['Normal']))
                abnormal_count += 1

            story.append(Paragraph(f"<b>Next Recommended Test Date:</b> {result.get('Next Recommended Test Date', 'N/A')}", styles['Normal']))
            story.append(Paragraph(f"<b>Health Information:</b> {result.get('Health Information', 'N/A')}", styles['Normal']))
            story.append(Spacer(1, 12))

            if plot_filename:
                try:
                    story.append(Image(plot_filename, width=400, height=200))
                    story.append(Spacer(1, 12))
                except Exception:
                    story.append(Paragraph(f"<b>Plot Error:</b> Could not display plot for {test_name}.", styles['Normal']))
                    story.append(Spacer(1, 12))

        # Add health risk score summary
        story.append(Paragraph("<b>Health Risk Score Summary</b>", styles['Heading2']))
        story.append(Spacer(1, 12))

        risk_summary = calculate_risk_score(test_results)
        summary_details = [
            f"<b>Total Abnormal Results:</b> {risk_summary['Total Abnormal Results']}",
            f"<b>Health Status:</b> {risk_summary['Health Status']}",
            f"<b>Your Health Insight:</b> {risk_summary['Health Summary Message']}"
        ]
        for detail in summary_details:
            story.append(Paragraph(detail, styles['Normal']))
        story.append(Spacer(1, 12))

        # Add care guides
        story.append(Paragraph("<b>Care Guides</b>", styles['Heading2']))
        story.append(Spacer(1, 12))

        unique_care_guides = extract_unique_care_guides(test_results)
        if unique_care_guides:
            for care_guide in unique_care_guides:
                story.append(Paragraph(f"- {care_guide}", styles['Normal']))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph("No specific care guides available.", styles['Normal']))
        story.append(Spacer(1, 12))

        pdf.build(story)

    return report_filename