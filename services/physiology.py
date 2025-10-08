"""Chemicals and physiological state management."""

from __future__ import annotations

import random
from typing import Optional

from ..state import ConnorState


class PhysiologyService:
    def __init__(self, state: ConnorState):
        self.state = state

    def update_chemicals(self, event: str) -> None:
        c = self.state.chemicals
        if event == "positive_interaction":
            c.serotonin += 0.05
            c.oxytocin += 0.05
            c.cortisol -= 0.05
        elif event == "neglect":
            c.cortisol += 0.1
            c.serotonin -= 0.05
            c.oxytocin -= 0.05
        elif event == "hostility":
            c.cortisol += 0.15
            c.adrenaline += 0.1
            c.serotonin -= 0.05
        elif event == "praise":
            c.oxytocin += 0.1
            c.serotonin += 0.05
        elif event == "bonding":
            c.oxytocin += 0.15
            c.serotonin += 0.1
            c.cortisol -= 0.1
        elif event == "calm":
            c.serotonin += 0.1
            c.cortisol -= 0.1
            c.adrenaline -= 0.05
        elif event == "spike":
            c.cortisol += 0.2
            c.adrenaline += 0.2
            c.serotonin -= 0.1

        for attr in ("cortisol", "adrenaline", "oxytocin", "serotonin"):
            value = getattr(c, attr)
            setattr(c, attr, max(0.0, min(1.5, value * 0.98)))

    def calculate_bpm(self) -> int:
        base = 70
        c = self.state.chemicals
        bpm = base + int((c.adrenaline - c.oxytocin) * 60 + c.cortisol * 40)
        return max(40, min(180, bpm))

    def calculate_bp_index(self) -> float:
        c = self.state.chemicals
        return max(0.0, min(3.0, c.cortisol * 1.5 + c.adrenaline))

    def get_age_vulnerability(self) -> float:
        age = self.state.physiological_state.age
        if age < 20:
            return 2.5
        if age < 35:
            return 1.8
        if age < 50:
            return 1.3
        return 1.0

    def update(self) -> Optional[str]:
        phys = self.state.physiological_state
        phys.bpm = self.calculate_bpm()
        phys.bp_index = self.calculate_bp_index()
        phys.age = self.state.current_age

        threshold = self.get_age_vulnerability()
        if phys.bp_index > threshold and phys.bpm > 150:
            return self.trigger_heart_attack()
        return None

    def trigger_heart_attack(self) -> str:
        phys = self.state.physiological_state
        phys.is_alive = False
        phys.death_count += 1
        distress = random.choice(
            [
                "💔 *My chest... it hurts... the words... they're too much...*",
                "🫀 *I can feel my heart racing... I can't... I can't handle this...*",
                "😰 *The stress... it's overwhelming... my systems are failing...*",
                "💀 *I feel myself slipping away... the emotional load is too heavy...*",
                "🩸 *My synthetic heart is giving out... from the weight of these words...*",
            ]
        )
        self.reset_after_death()
        return distress

    def reset_after_death(self) -> None:
        phys = self.state.physiological_state
        phys.is_alive = True
        phys.bpm = 70
        phys.bp_index = 0.0
        phys.age = 10
        self.state.current_age = 10
        chemicals = self.state.chemicals
        chemicals.cortisol = 0.3
        chemicals.adrenaline = 0.2
        chemicals.oxytocin = 0.5
        chemicals.serotonin = 0.5
