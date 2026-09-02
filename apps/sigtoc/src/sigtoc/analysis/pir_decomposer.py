import os
import uuid
import json
from typing import List, Optional

from pydantic import BaseModel
from anthropic import Anthropic

from shared.models import Requirement, SIR, Indicator

class DecomposedPIR(BaseModel):
    requirement: Requirement
    sirs: List[SIR]
    indicators: List[Indicator]

class PIRDecomposer:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def decompose(self, requirement: Requirement, context: str) -> DecomposedPIR:
        if self.client:
            return self._decompose_with_claude(requirement, context)
        else:
            return self._decompose_with_heuristics(requirement, context)

    def _decompose_with_claude(self, requirement: Requirement, context: str) -> DecomposedPIR:
        prompt = f"""
        Decompose the following Priority Intelligence Requirement (PIR) into Specific Intelligence Requirements (SIRs) and Indicators.
        PIR Question: {requirement.question}
        Context: {context}
        
        Generate 3-5 SIRs. For each SIR, generate 1-3 Indicators.
        """
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            tools=[{
                "name": "decompose_pir",
                "description": "Decompose PIR into SIRs and Indicators",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sirs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "dimensions": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "indicators": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "description": {"type": "string"},
                                                "observable_pattern": {"type": "string"},
                                                "volatility": {"type": "string", "enum": ["low", "medium", "high"]}
                                            },
                                            "required": ["description", "observable_pattern"]
                                        }
                                    }
                                },
                                "required": ["question", "dimensions", "indicators"]
                            }
                        }
                    },
                    "required": ["sirs"]
                }
            }],
            tool_choice={"type": "tool", "name": "decompose_pir"},
            messages=[{"role": "user", "content": prompt}]
        )
        
        sirs_list = []
        indicators_list = []
        
        for content in response.content:
            if content.type == "tool_use" and content.name == "decompose_pir":
                sirs_data = content.input.get("sirs", [])
                for sir_data in sirs_data:
                    sir_id = str(uuid.uuid4())
                    sir = SIR(
                        sir_id=sir_id,
                        req_id=requirement.req_id,
                        question=sir_data["question"],
                        dimensions=sir_data.get("dimensions", [])
                    )
                    sirs_list.append(sir)
                    
                    for ind_data in sir_data.get("indicators", []):
                        indicator = Indicator(
                            indicator_id=str(uuid.uuid4()),
                            sir_id=sir_id,
                            description=ind_data["description"],
                            observable_pattern=ind_data["observable_pattern"],
                            volatility=ind_data.get("volatility", "medium")
                        )
                        indicators_list.append(indicator)
                
                return DecomposedPIR(
                    requirement=requirement,
                    sirs=sirs_list,
                    indicators=indicators_list
                )
                
        return self._decompose_with_heuristics(requirement, context)

    def _decompose_with_heuristics(self, requirement: Requirement, context: str) -> DecomposedPIR:
        sir1_id = str(uuid.uuid4())
        sir2_id = str(uuid.uuid4())
        sir3_id = str(uuid.uuid4())
        sir4_id = str(uuid.uuid4())
        
        sirs = [
            SIR(
                sir_id=sir1_id,
                req_id=requirement.req_id,
                question=f"Which adversary groups or violent criminal entities are active in {context}?",
                dimensions=["terrorism", "violent_crime"]
            ),
            SIR(
                sir_id=sir2_id,
                req_id=requirement.req_id,
                question=f"What civil unrest, protests, or legal detention risks exist in {context}?",
                dimensions=["civil_unrest", "legal_detention"]
            ),
            SIR(
                sir_id=sir3_id,
                req_id=requirement.req_id,
                question=f"Are there active technical surveillance or cyber espionage campaigns targeting travelers in {context}?",
                dimensions=["espionage"]
            ),
            SIR(
                sir_id=sir4_id,
                req_id=requirement.req_id,
                question=f"How resilient are local infrastructure, medical facilities, and environmental systems in {context}?",
                dimensions=["infrastructure", "health_medical", "natural_hazards"]
            )
        ]
        
        indicators = [
            Indicator(
                indicator_id=str(uuid.uuid4()),
                sir_id=sir1_id,
                description="Reports of violent incidents or extremist activity",
                observable_pattern="keyword match: attack, blast, militia, cartel, kidnapper",
                volatility="high"
            ),
            Indicator(
                indicator_id=str(uuid.uuid4()),
                sir_id=sir2_id,
                description="Demonstration permits and social unrest reports",
                observable_pattern="keyword match: protest, strike, demonstration, curfew",
                volatility="medium"
            ),
            Indicator(
                indicator_id=str(uuid.uuid4()),
                sir_id=sir3_id,
                description="State surveillance advisories or airport device check warnings",
                observable_pattern="keyword match: interception, wiretap, device seizure, malware",
                volatility="low"
            ),
            Indicator(
                indicator_id=str(uuid.uuid4()),
                sir_id=sir4_id,
                description="Hospital capacity and transport infrastructure notices",
                observable_pattern="keyword match: road closure, flight cancellation, epidemic",
                volatility="medium"
            )
        ]
        
        return DecomposedPIR(
            requirement=requirement,
            sirs=sirs,
            indicators=indicators
        )
