import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from src.models.explainability import ExplainerWrapper

def test_explain_prediction_format():
    """
    Verifies the SHAP wrapper outputs the exact JSON format required
    by the Prediction schema.
    """
    # Create a real dummy model so SHAP TreeExplainer accepts it
    df = pd.DataFrame({'traffic_score': [0.1, 0.9, 0.5], 'weather_severity': [0, 2, 1]})
    y = [10, 50, 30]
    model = DecisionTreeRegressor(max_depth=2, random_state=42)
    model.fit(df, y)
    
    wrapper = ExplainerWrapper(model)
    
    # Predict on one row
    features_df = pd.DataFrame({'traffic_score': [0.82], 'weather_severity': [1]})
    
    explanation = wrapper.explain_prediction(features_df, top_k=2)
    
    # Since there's only 1 instance, it should return a single list
    assert isinstance(explanation, list)
    assert len(explanation) == 2
    
    # Verify the dictionary structure matches the schema requirements
    assert "feature" in explanation[0]
    assert "value" in explanation[0]
    assert "impact_minutes" in explanation[0]
    
    # Ensure types are schema compliant
    assert isinstance(explanation[0]['feature'], str)
    assert isinstance(explanation[0]['value'], (float, int, str))
    assert isinstance(explanation[0]['impact_minutes'], float)
