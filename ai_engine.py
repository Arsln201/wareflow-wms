from datetime import date
from wareflow_capabilities import get_wareflow_capabilities

def calculate_risk_score(product):
    """
    Calculate a 0–100 inventory risk score.

    Risk factors:
    - Expiry severity: 0–70
    - Stock level: 0–20
    - Financial exposure: 0–10
    """

    score = 0
    reasons = []

    quantity = int(product.quantity or 0)
    unit_cost = float(product.unit_cost or 0)

    stock_value = quantity * unit_cost

    today = date.today()

    days_remaining = None

    # ======================================
    # 1. EXPIRY RISK — MAX 70
    # ======================================

    if product.expiry_date:

        days_remaining = (
            product.expiry_date - today
        ).days

        if days_remaining < 0:

            score += 70

            reasons.append(
                f"Expired {abs(days_remaining)} days ago."
            )

        elif days_remaining == 0:

            score += 65

            reasons.append(
                "Expires today."
            )

        elif days_remaining <= 3:

            score += 60

            reasons.append(
                f"Expires in {days_remaining} days."
            )

        elif days_remaining <= 7:

            score += 50

            reasons.append(
                f"Expires in {days_remaining} days."
            )

        elif days_remaining <= 14:

            score += 40

            reasons.append(
                f"Expires in {days_remaining} days."
            )

        elif days_remaining <= 30:

            score += 25

            reasons.append(
                f"Expires in {days_remaining} days."
            )

    # ======================================
    # 2. STOCK RISK — MAX 20
    # ======================================

    if quantity <= 2:

        score += 20

        reasons.append(
            f"Critical stock level: only {quantity} units."
        )

    elif quantity <= 5:

        score += 15

        reasons.append(
            f"Very low stock: {quantity} units remaining."
        )

    elif quantity <= 10:

        score += 10

        reasons.append(
            f"Low stock: {quantity} units remaining."
        )

    elif quantity <= 20:

        score += 5

        reasons.append(
            f"Stock level is getting low: {quantity} units."
        )

    # ======================================
    # 3. FINANCIAL EXPOSURE — MAX 10
    # ======================================

    if stock_value >= 5000:

        score += 10

        reasons.append(
            f"₹{stock_value:,.2f} inventory value is exposed."
        )

    elif stock_value >= 2500:

        score += 8

        reasons.append(
            f"₹{stock_value:,.2f} inventory value is exposed."
        )

    elif stock_value >= 1000:

        score += 6

        reasons.append(
            f"₹{stock_value:,.2f} inventory value is exposed."
        )

    elif stock_value >= 500:

        score += 4

        reasons.append(
            f"₹{stock_value:,.2f} inventory value is exposed."
        )

    elif stock_value >= 250:

        score += 2

        reasons.append(
            f"₹{stock_value:,.2f} inventory value is exposed."
        )

    # ======================================
    # FINAL SCORE
    # ======================================

    score = min(score, 100)

    # ======================================
    # PRIORITY
    # ======================================

    if score >= 81:

        priority = "CRITICAL"

        action = (
            "Immediate action required. "
            "Review, isolate, or remove this inventory."
        )

    elif score >= 61:

        priority = "HIGH"

        action = (
            "Prioritize this product "
            "before lower-risk inventory."
        )

    elif score >= 31:

        priority = "MEDIUM"

        action = (
            "Monitor this product "
            "and plan corrective action."
        )

    else:

        priority = "LOW"

        action = (
            "No immediate action required. "
            "Continue monitoring."
        )

    # ======================================
    # HEALTHY PRODUCT
    # ======================================

    if score == 0:

        reasons.append(
            "No significant inventory risk detected."
        )

    return {
        "score": score,
        "priority": priority,
        "stock_value": stock_value,
        "days_remaining": days_remaining,
        "reasons": reasons,
        "action": action
    }

def calculate_inventory_risk(products):

    risk_items = []

    for product in products:

        risk = calculate_risk_score(product)

        # Only show products that actually have risk
        if risk["score"] > 0:

            risk_items.append({
                "product": product.product_name,
                "sku": product.sku,
                "quantity": product.quantity,
                "score": risk["score"],
                "priority": risk["priority"],
                "stock_value": risk["stock_value"],
                "days_remaining": risk["days_remaining"],
                "reasons": risk["reasons"],
                "action": risk["action"]
            })

    # Highest risk first
    risk_items.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return risk_items

def analyze_warehouse(products):
    """
    Analyze current inventory and return
    actionable warehouse intelligence.
    """

    insights = []

    today = date.today()

    for product in products:

        # ==========================================
        # OUT OF STOCK
        # ==========================================

        if product.quantity <= 0:

            insights.append({
                "type": "OUT_OF_STOCK",
                "severity": "critical",
                "product": product.product_name,
                "sku": product.sku,
                "message": (
                    f"{product.product_name} is out of stock."
                )
            })

            continue

        # ==========================================
        # LOW STOCK
        # ==========================================

        if product.quantity <= 10:

            insights.append({
                "type": "LOW_STOCK",
                "severity": "warning",
                "product": product.product_name,
                "sku": product.sku,
                "message": (
                    f"{product.product_name} has only "
                    f"{product.quantity} units remaining."
                )
            })

        # ==========================================
        # EXPIRY ANALYSIS
        # ==========================================

        if product.expiry_date:

            days_remaining = (
                product.expiry_date - today
            ).days

            # Already expired
            if days_remaining < 0:

                insights.append({
                    "type": "EXPIRED",
                    "severity": "critical",
                    "product": product.product_name,
                    "sku": product.sku,
                    "message": (
                        f"{product.product_name} has expired."
                    ),
                    "days": days_remaining
                })

            # Expiring within 7 days
            elif days_remaining <= 7:

                insights.append({
                    "type": "EXPIRING_SOON",
                    "severity": "critical",
                    "product": product.product_name,
                    "sku": product.sku,
                    "message": (
                        f"{product.product_name} expires "
                        f"in {days_remaining} days."
                    ),
                    "days": days_remaining
                })

            # Expiring within 30 days
            elif days_remaining <= 30:

                insights.append({
                    "type": "EXPIRING_SOON",
                    "severity": "warning",
                    "product": product.product_name,
                    "sku": product.sku,
                    "message": (
                        f"{product.product_name} expires "
                        f"in {days_remaining} days."
                    ),
                    "days": days_remaining
                })

    # ==========================================
    # SORT BY SEVERITY
    # ==========================================

    severity_order = {
        "critical": 0,
        "warning": 1,
        "info": 2,
        "success": 3
    }

    insights.sort(
        key=lambda item:
        severity_order.get(
            item["severity"],
            99
        )
    )

    return insights

def generate_recommendations(insights):
    """
    Convert warehouse insights into actionable
    recommendations for Admins and Managers.
    """

    recommendations = []

    # ==========================================
    # EXPIRED STOCK
    # ==========================================

    expired = [
        item
        for item in insights
        if item["type"] == "EXPIRED"
    ]

    if expired:

        recommendations.append({
            "type": "EXPIRED_STOCK",
            "priority": "HIGH",
            "title": "Remove expired inventory",
            "message": (
                f"{len(expired)} product(s) have expired "
                "stock and should be isolated from active inventory."
            )
        })

    # ==========================================
    # EXPIRING SOON
    # ==========================================

    expiring = [
        item
        for item in insights
        if item["type"] == "EXPIRING_SOON"
    ]

    if expiring:

        recommendations.append({
            "type": "EXPIRY_RISK",
            "priority": "HIGH",
            "title": "Prioritize expiring products",
            "message": (
                f"{len(expiring)} product(s) are approaching "
                "their expiry date. Consider FEFO handling."
            )
        })

    # ==========================================
    # OUT OF STOCK
    # ==========================================

    out_of_stock = [
        item
        for item in insights
        if item["type"] == "OUT_OF_STOCK"
    ]

    if out_of_stock:

        recommendations.append({
            "type": "REORDER",
            "priority": "HIGH",
            "title": "Reorder required",
            "message": (
                f"{len(out_of_stock)} product(s) are completely "
                "out of stock."
            )
        })

    # ==========================================
    # LOW STOCK
    # ==========================================

    low_stock = [
        item
        for item in insights
        if item["type"] == "LOW_STOCK"
    ]

    if low_stock:

        recommendations.append({
            "type": "LOW_STOCK",
            "priority": "MEDIUM",
            "title": "Review low-stock inventory",
            "message": (
                f"{len(low_stock)} product(s) have "
                "10 or fewer units remaining."
            )
        })

    # ==========================================
    # NOTHING TO REPORT
    # ==========================================

    if not recommendations:

        recommendations.append({
            "type": "HEALTHY",
            "priority": "LOW",
            "title": "Inventory looks healthy",
            "message": (
                "No critical inventory actions are currently required."
            )
        })

    return recommendations

def calculate_value_at_risk(products):
    """
    Calculate inventory value exposed to expiry risk.

    Includes:
    - Already expired stock
    - Stock expiring within 30 days
    """

    today = date.today()

    total_value = 0
    expired_value = 0
    expiring_value = 0

    risk_products = []

    for product in products:

        if product.quantity <= 0:
            continue

        if not product.expiry_date:
            continue

        days_remaining = (
            product.expiry_date - today
        ).days

        stock_value = (
            product.quantity *
            float(product.unit_cost or 0)
        )

        # --------------------------------------
        # EXPIRED
        # --------------------------------------

        if days_remaining < 0:

            expired_value += stock_value
            total_value += stock_value

            risk_products.append({
                "product": product.product_name,
                "sku": product.sku,
                "quantity": product.quantity,
                "unit_cost": float(product.unit_cost or 0),
                "value": stock_value,
                "status": "EXPIRED",
                "days": days_remaining
            })

        # --------------------------------------
        # EXPIRING SOON
        # --------------------------------------

        elif days_remaining <= 30:

            expiring_value += stock_value
            total_value += stock_value

            risk_products.append({
                "product": product.product_name,
                "sku": product.sku,
                "quantity": product.quantity,
                "unit_cost": float(product.unit_cost or 0),
                "value": stock_value,
                "status": "EXPIRING SOON",
                "days": days_remaining
            })

    # Highest financial risk first
    risk_products.sort(
        key=lambda item: item["value"],
        reverse=True
    )

    return {
        "total_value": total_value,
        "expired_value": expired_value,
        "expiring_value": expiring_value,
        "products": risk_products
    }
    
    def build_wareflow_ai_context(inventory_risk):

     capabilities = get_wareflow_capabilities()

     return {
        "capabilities": capabilities,
        "inventory_risk": inventory_risk
    }
     
def build_wareflow_ai_prompt(question, inventory_risk):

    capabilities = get_wareflow_capabilities()

    available = ", ".join(
        capabilities["available"]
    )

    planned = ", ".join(
        capabilities["planned"]
    )

    risk_context = []

    for item in inventory_risk[:10]:

        risk_context.append({
            "product": item["product"],
            "sku": item["sku"],
            "quantity": item["quantity"],
            "risk_score": item["score"],
            "priority": item["priority"],
            "stock_value": item["stock_value"],
            "days_remaining": item["days_remaining"],
            "reasons": item["reasons"],
            "recommended_action": item["action"]
        })

    return f"""
You are WareFlow AI, an intelligent warehouse operations assistant.

Your job is to help warehouse users understand their current
inventory and make operational decisions.

CURRENTLY AVAILABLE WAREFLOW CAPABILITIES:
{available}

PLANNED FUTURE CAPABILITIES:
{planned}

IMPORTANT RULE:
Never pretend a planned capability is currently available.

If the user asks about a planned capability, clearly explain that
the feature is planned for a future version and then offer the
closest currently available alternative.

CURRENT INVENTORY RISK DATA:
{risk_context}

USER QUESTION:
{question}

Answer using the warehouse data provided above.

Be concise, practical and professional.

When recommending an action, prioritize higher-risk inventory first.

Do not invent inventory numbers, products, scores or capabilities.
"""