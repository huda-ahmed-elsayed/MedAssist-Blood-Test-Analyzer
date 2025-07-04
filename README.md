# MedAssist Blood Test Analyzer

A smart, rule-based system for analyzing, monitoring, and predicting medical blood test results.  
This module is part of the MedAssist healthcare platform.

---

## 🔬 Features

- ✅ Classifies test results as Low / Normal / High
- ✅ Generates health insights, care guides, and retest recommendations
- ✅ Monitors patient progress using trend analysis
- ✅ Predicts future test values using linear regression
- ✅ Integrates with Firebase Firestore for medical reference data
- ✅ Automatically generates visual reports

---

## 🧠 Technologies Used

- Python 3  
- Firebase Firestore  
- Matplotlib  
- Scikit-learn (for Linear Regression)  
- ReportLab (for PDF generation)

---

## 📁 Main Modules

| File | Description |
|------|-------------|
| `classify_test_result()` | Classifies test values and generates full report |
| `analyze_trend_from_firestore()` | Detects changes over time and sets monitoring priority |
| `predict_all_next_values_from_firestore()` | Forecasts future test results (30-day prediction) |
| `generate_medical_report_from_firestore()` | Produces PDF report with graphs, insights, and suggestions |
| `calculate_risk_score()` | Calculates a health risk score based on multiple results |
| `extract_unique_care_guides()` | Extracts custom care guides from medical knowledge base |

---

## 📊 Sample Output

- JSON result summary per test
- Trend label (Increasing / Decreasing / Stable)
- Monitoring suggestion (e.g., weekly or every 3 months)
- Predicted next value
- PDF medical report with charts

---

## 📌 Future Improvements

- Arabic language support for reports and chatbot interaction  
- OCR integration to scan lab reports  
- Improved prediction using ML models (e.g., LSTM)  
- Dynamic reference ranges (age/gender-based)

---

## 📃 License

This module is released as part of my graduation project and is open for educational and research use.
