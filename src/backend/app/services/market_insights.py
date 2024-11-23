from typing import Dict, List, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

class MarketInsight(BaseModel):
    median_price: float
    days_on_market: int
    price_trend: float  # percentage change
    similar_listings: int
    comp_prices: List[float]
    market_status: str  # "buyer's market", "seller's market", "balanced"
    zip_code: str
    last_updated: datetime

class MarketInsightsService:
    def __init__(self):
        self.cache: Dict[str, MarketInsight] = {}
        self.cache_duration = timedelta(hours=12)

    async def get_market_insights(self, zip_code: str, property_type: str = "single_family") -> Optional[MarketInsight]:
        """Get real-time market insights for a specific area."""
        try:
            # Check cache first
            cache_key = f"{zip_code}_{property_type}"
            if cache_key in self.cache:
                insight = self.cache[cache_key]
                if datetime.now() - insight.last_updated < self.cache_duration:
                    return insight

            # Simulate real estate market data (in production, this would call real APIs)
            insight = await self._fetch_market_data(zip_code, property_type)
            
            # Cache the result
            self.cache[cache_key] = insight
            return insight

        except Exception as e:
            logger.error(f"Error fetching market insights: {e}")
            return None

    async def _fetch_market_data(self, zip_code: str, property_type: str) -> MarketInsight:
        """Fetch market data from various sources."""
        # In production, this would make API calls to real estate data providers
        # For now, we'll return simulated data
        return MarketInsight(
            median_price=500000,
            days_on_market=15,
            price_trend=3.5,  # 3.5% increase
            similar_listings=12,
            comp_prices=[485000, 510000, 495000, 525000],
            market_status="seller's market",
            zip_code=zip_code,
            last_updated=datetime.now()
        )

    def generate_market_insight_phrases(self, insight: MarketInsight) -> List[str]:
        """Generate natural language phrases about market conditions."""
        phrases = []
        
        # Median price context
        phrases.append(
            f"In this area, homes are typically selling for around ${insight.median_price:,.0f}"
        )
        
        # Days on market context
        if insight.days_on_market < 7:
            phrases.append(
                f"Properties here are moving very quickly, typically selling within {insight.days_on_market} days"
            )
        elif insight.days_on_market < 14:
            phrases.append(
                f"The market is active, with homes selling in about {insight.days_on_market} days"
            )
        else:
            phrases.append(
                f"Properties in this area typically take about {insight.days_on_market} days to sell"
            )
        
        # Price trend context
        if insight.price_trend > 0:
            phrases.append(
                f"We're seeing home values increase by {abs(insight.price_trend):.1f}% in this neighborhood"
            )
        elif insight.price_trend < 0:
            phrases.append(
                f"Home prices have adjusted down by {abs(insight.price_trend):.1f}% recently"
            )
        
        # Competition context
        if insight.similar_listings < 5:
            phrases.append(
                f"There are only {insight.similar_listings} similar properties available right now"
            )
        else:
            phrases.append(
                f"There are {insight.similar_listings} comparable properties on the market"
            )
        
        # Market status context
        if insight.market_status == "seller's market":
            phrases.append(
                "Currently it's a seller's market, so desirable properties move quickly"
            )
        elif insight.market_status == "buyer's market":
            phrases.append(
                "Buyers have good negotiating power in the current market"
            )
        else:
            phrases.append(
                "The market is fairly balanced between buyers and sellers right now"
            )
        
        return phrases

    def get_market_recommendation(self, insight: MarketInsight, list_price: float) -> str:
        """Generate a strategic recommendation based on market conditions."""
        # Compare list price to median
        price_diff_percent = (list_price - insight.median_price) / insight.median_price * 100
        
        if insight.market_status == "seller's market":
            if price_diff_percent > 10:
                return "While it's a seller's market, this price point is notably above the median. We should highlight the property's unique features that justify the premium."
            else:
                return "The strong seller's market supports this price point, and properties are moving quickly."
        elif insight.market_status == "buyer's market":
            if price_diff_percent > 5:
                return "Given the current buyer's market, we might want to discuss price flexibility or emphasize special features."
            else:
                return "The price point is competitive for the current market conditions, which should attract serious buyers."
        else:
            if abs(price_diff_percent) < 5:
                return "The price aligns well with market conditions, making it attractive to qualified buyers."
            elif price_diff_percent > 0:
                return "We're slightly above market median, but can justify this with the property's features."
            else:
                return "This property represents good value in the current market."

market_insights = MarketInsightsService()