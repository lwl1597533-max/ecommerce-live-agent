from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class Product(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0, allow_inf_nan=False)
    original_price: float | None = Field(None, gt=0, allow_inf_nan=False)
    specs: dict = Field(default_factory=dict)
    ingredients: list[str] | None = None
    description: str = Field(min_length=1, max_length=5000)
    highlights: list[str] = Field(default_factory=list, max_length=20)
    reviews: list[dict] = Field(default_factory=list, max_length=20)
    stock: int | None = Field(None, ge=0)
    promo: dict | None = None
    target_audience: str | None = None

class SellingPoint(BaseModel):
    point: str
    evidence: str
    target_user: str
    priority: int = Field(ge=1, le=5)

class SellingPointResult(BaseModel):
    product_id: str
    selling_points: list[SellingPoint] = Field(min_length=3, max_length=5)
    summary: str

class ScriptType(str, Enum):
    OPENING = 'opening'
    INTRO = 'intro'
    PROMOTE = 'promote'
    CLOSE = 'close'

class StyleType(str, Enum):
    PASSIONATE = 'passionate'
    PROFESSIONAL = 'professional'
    HUMOROUS = 'humorous'

class ScriptRequest(BaseModel):
    product: Product
    script_type: ScriptType
    style: StyleType = StyleType.PASSIONATE
    duration_seconds: int = Field(60, ge=15, le=300)
    stream: bool = True

class Turn(BaseModel):
    question: str = Field(max_length=1000)
    reply: str = Field(max_length=2000)

class InteractionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    product: Product
    context: list[Turn] = Field(default_factory=list, max_length=10)

Intent = Literal['price', 'specs', 'shipping', 'effect', 'comparison', 'authenticity', 'after_sale', 'other']

class IntentResult(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)

class InteractionResponse(IntentResult):
    reply: str
    should_promote: bool = False

class Feedback(BaseModel):
    generation_id: str
    rating: Literal[-1, 1]
