from lineageguard.context import DataHubMCPContextProvider


def test_mcp_payload_is_normalized_into_ml_entities() -> None:
    payload = {
        "searchResults": [
            {
                "entity": {
                    "urn": "urn:li:mlFeature:(customer_features,customer_age)",
                    "type": "mlFeature",
                    "name": "customer_age",
                }
            },
            {
                "entity": {
                    "urn": (
                        "urn:li:mlModel:(urn:li:dataPlatform:mlflow,"
                        "churn-model-v3,PROD)"
                    ),
                    "type": "mlModel",
                    "name": "churn-model-v3",
                    "tags": [{"urn": "urn:li:tag:Tier1"}],
                }
            },
        ]
    }

    entities = DataHubMCPContextProvider._extract_entities(payload)

    assert {entity.entity_type for entity in entities} == {"mlFeature", "mlModel"}
    assert next(entity for entity in entities if entity.entity_type == "mlModel").tags == [
        "Tier1"
    ]
