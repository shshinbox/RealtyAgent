from gliner import GLiNER
import torch


class PersonaExtractor:
    def __init__(self, model_name: str = "urchade/gliner_multi-v2.1"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = GLiNER.from_pretrained(model_name).to(self.device)

        self.labels = [
            "location",
            "budget",
            "property_type",
            "amenity",
            "building_age",
        ]

    def extract(self, text: str) -> dict:
        entities = self.model.predict_entities(text, self.labels)

        result = {}
        for entity in entities:
            label = entity["label"]
            value = entity["text"]
            if label in result:
                if isinstance(result[label], list):
                    result[label].append(value)
                else:
                    result[label] = [result[label], value]
            else:
                result[label] = value
        return result
