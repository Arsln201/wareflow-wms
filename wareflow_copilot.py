# ==========================================
# WAREFLOW AI COPILOT
# 100% LOCAL / FREE
# ==========================================

from wareflow_capabilities import get_wareflow_capabilities


def answer_warehouse_question(
    question,
    inventory_risk,
    value_at_risk=None,
    context=None
):
    
    question = question.strip().lower()
    
    context = context or {}
    
    """
    Answer common warehouse questions using
    current WareFlow data.

    No external API is used.
    """

    question = question.strip().lower()

    capabilities = get_wareflow_capabilities()

    # ======================================
    # NO QUESTION
    # ======================================

    if not question:
        return "Please enter a warehouse question."


    # ======================================
    # FOLLOW-UP: "WHICH ONE?"
    # ======================================

    if (
        "which one" in question
        or "which is the worst" in question
        or "which one is worst" in question
        or "who is the worst" in question
        or "what is the worst one" in question
    ):

        previous_items = context.get(
            "last_items",
            []
        )

        if previous_items:

            worst = previous_items[0]

            return (
                f"🔴 {worst['product']} is the "
                f"highest-risk item from the previous "
                f"results.\n\n"
                f"Risk score: {worst['score']}/100 "
                f"({worst['priority']})\n"
                f"Recommended action: "
                f"{worst['action']}"
            )

        if inventory_risk:

            worst = inventory_risk[0]

            return (
                f"🔴 {worst['product']} is currently "
                f"the highest-risk item.\n\n"
                f"Risk score: {worst['score']}/100 "
                f"({worst['priority']})"
            )

        return (
            "I don't currently have a previous "
            "risk result to compare."
        )

    # ======================================
    # FOLLOW-UP: "WHAT SHOULD I DO?"
    # ======================================

    if (
        "what should i do about it" in question
        or "what should i do" in question
        or "what do i do about it" in question
        or "what action should i take" in question
        or "what should i handle" in question
    ):

        previous_product = context.get(
            "last_product"
        )

        if previous_product:

            return (
                f"🎯 Recommended Action — "
                f"{previous_product['product']}\n\n"
                f"Risk score: "
                f"{previous_product['score']}/100 "
                f"({previous_product['priority']})\n\n"
                f"Action:\n"
                f"{previous_product['action']}"
            )

        return (
            "Tell me which product you want me "
            "to recommend an action for."
        )


    # ======================================
    # PRODUCT SWITCH
    # ======================================

    for item in inventory_risk:

        product_name = (
            item["product"] or ""
        ).lower()

        sku = (
            item["sku"] or ""
        ).lower()

        if (
            product_name
            and product_name in question
        ) or (
            sku
            and sku in question
        ):

            if (
                "what about" in question
                or "how about" in question
                or "tell me about" in question
                or "what is the risk" in question
                or "risk of" in question
            ):

                return (
                    f"🔎 {item['product']} Risk\n\n"
                    f"Risk score: "
                    f"{item['score']}/100 "
                    f"({item['priority']})\n"
                    f"Quantity: "
                    f"{item['quantity']} units\n\n"
                    f"Recommended action:\n"
                    f"{item['action']}"
                )

    # ======================================
    # RISKY PRODUCTS
    # ======================================

    if (
        "which products are risky" in question
        or "show risky products" in question
        or "show risky inventory" in question
        or "what products are risky" in question
        or "what inventory is risky" in question
        or "which inventory is risky" in question
        or "risky products" in question
        or "risky inventory" in question
        or "high risk products" in question
        or "high risk inventory" in question
    ):

        risky_items = [
            item
            for item in inventory_risk
            if item["score"] >= 40
        ]

        if not risky_items:

            return (
                "🟢 No significant inventory risks "
                "were detected.\n\n"
                "Your current warehouse inventory "
                "looks healthy."
            )

        answer = (
            "⚠️ Risky Inventory\n\n"
            f"{len(risky_items)} product(s) "
            "currently require attention:\n\n"
        )

        for item in risky_items[:5]:

            answer += (
                f"• {item['product']} — "
                f"{item['score']}/100 "
                f"({item['priority']})\n"
            )

            answer += (
                f"  Action: {item['action']}\n\n"
            )

        return answer

    # ======================================
    # HIGHEST RISK
    # ======================================

    if (
        "highest risk" in question
        or "most risky" in question
        or "riskiest" in question
        or "risk product" in question
    ):

        if not inventory_risk:

            return (
                "Your inventory currently has "
                "no significant risks."
            )

        item = inventory_risk[0]

        answer = (
            f"🔴 {item['product']} is currently "
            f"the highest-risk product.\n\n"
            f"Risk score: {item['score']}/100 "
            f"({item['priority']})\n"
            f"Quantity: {item['quantity']} units\n"
        )

        if item["stock_value"]:

            answer += (
                f"Inventory value: "
                f"₹{item['stock_value']:,.2f}\n"
            )

        if item["reasons"]:

            answer += "\nWhy:\n"

            for reason in item["reasons"][:3]:

                answer += f"• {reason}\n"

        answer += (
            f"\nRecommended action:\n"
            f"{item['action']}"
        )

        return answer


    # ======================================
    # WHAT SHOULD I HANDLE FIRST?
    # ======================================

    if (
        "handle first" in question
        or "do first" in question
        or "priority" in question
        or "prioritize" in question
        or "what should i" in question
    ):

        if not inventory_risk:

            return (
                "Your warehouse currently looks healthy. "
                "There are no significant inventory risks "
                "requiring immediate attention."
            )

        top_items = inventory_risk[:3]

        answer = (
            "Here are the highest-priority items "
            "to handle:\n\n"
        )

        for index, item in enumerate(
            top_items,
            start=1
        ):

            answer += (
                f"{index}. {item['product']} — "
                f"{item['score']}/100 "
                f"({item['priority']})\n"
            )

            answer += (
                f"   Action: {item['action']}\n\n"
            )

        return answer


    # ======================================
    # EXPIRING PRODUCTS
    # ======================================

    if (
        "expir" in question
        or "expiry" in question
        or "expire" in question
    ):

        expiring = []

        for item in inventory_risk:

            days = item["days_remaining"]

            if days is not None and days <= 30:

                expiring.append(item)

        if not expiring:

            return (
                "I couldn't find inventory expiring "
                "within the next 30 days."
            )

        answer = (
            f"I found {len(expiring)} product(s) "
            f"with expiry risk:\n\n"
        )

        for item in expiring[:5]:

            days = item["days_remaining"]

            if days < 0:

                status = (
                    f"expired {abs(days)} days ago"
                )

            elif days == 0:

                status = "expires today"

            else:

                status = f"expires in {days} days"

            answer += (
                f"• {item['product']} — "
                f"{status} — "
                f"Risk {item['score']}/100\n"
            )

        return answer


    # ======================================
    # INVENTORY VALUE
    # ======================================

    if (
        "value at risk" in question
        or "inventory value" in question
        or "money at risk" in question
        or "financial risk" in question
    ):

        if value_at_risk:

            total = value_at_risk.get(
                "total_value",
                0
            )

            expired = value_at_risk.get(
                "expired_value",
                0
            )

            expiring = value_at_risk.get(
                "expiring_value",
                0
            )

            return (
                "💰 Inventory Value at Risk\n\n"
                f"Total exposed value: "
                f"₹{total:,.2f}\n"
                f"Expired inventory: "
                f"₹{expired:,.2f}\n"
                f"Expiring soon: "
                f"₹{expiring:,.2f}\n"
            )

        return (
            "Inventory value-at-risk data "
            "is currently unavailable."
        )


    # ======================================
    # LOW STOCK
    # ======================================

    if (
        "low stock" in question
        or "low inventory" in question
        or "running low" in question
        or "stock running" in question
    ):

        low_stock = []

        for item in inventory_risk:

            if item["quantity"] <= 10:

                low_stock.append(item)

        if not low_stock:

            return (
                "I don't see any products with "
                "critically low stock."
            )

        answer = (
            f"I found {len(low_stock)} product(s) "
            f"with low stock:\n\n"
        )

        for item in low_stock[:5]:

            answer += (
                f"• {item['product']} — "
                f"{item['quantity']} units "
                f"({item['priority']})\n"
            )

        return answer


    # ======================================
    # FUTURE CAPABILITIES
    # ======================================

    planned_keywords = {

        "forecast": "demand forecasting",

        "prediction": "advanced predictive analytics",

        "replenish": "automatic stock replenishment",

        "supplier": "supplier analytics",

        "employee": "employee task optimization",

        "task": "employee task optimization",

        "movement": "warehouse movement optimization",

        "automate": "automated warehouse actions",

    }


    for keyword, capability in planned_keywords.items():

        if keyword in question:

            if capability in capabilities["planned"]:

                return (
                    f"That feature isn't available "
                    f"in the current version of WareFlow yet.\n\n"
                    f"📌 Planned capability:\n"
                    f"{capability.title()}\n\n"
                    f"Currently, I can help with "
                    f"inventory analysis, expiry risk, "
                    f"risk scoring, value at risk, "
                    f"and warehouse recommendations."
                )


    # ======================================
    # HELP
    # ======================================

    if (
        "help" in question
        or "what can you do" in question
        or "capabilities" in question
        or "what can wareflow" in question
    ):

        available = capabilities["available"]

        answer = (
            "🤖 Here's what I can currently help "
            "with:\n\n"
        )

        for capability in available:

            answer += (
                f"• {capability.title()}\n"
            )

        answer += (
            "\nFuture capabilities such as demand "
            "forecasting and automatic replenishment "
            "are planned for later versions."
        )

        return answer


    # ======================================
    # WAREHOUSE HEALTH REPORT
    # ======================================

    if (
        "health report" in question
        or "warehouse health" in question
        or "warehouse status" in question
        or "overall health" in question
        or "how is my warehouse" in question
        or "how is the warehouse" in question
    ):

        if not inventory_risk:

            return (
                "🟢 Warehouse Health: HEALTHY\n\n"
                "No significant inventory risks were detected."
            )

        critical = [
            item for item in inventory_risk
            if item["priority"] == "CRITICAL"
        ]

        high = [
            item for item in inventory_risk
            if item["priority"] == "HIGH"
        ]

        medium = [
            item for item in inventory_risk
            if item["priority"] == "MEDIUM"
        ]

        low = [
            item for item in inventory_risk
            if item["priority"] == "LOW"
        ]

        if critical:

            health = "🔴 CRITICAL"

        elif high:

            health = "🟠 NEEDS ATTENTION"

        elif medium:

            health = "🟡 MODERATE"

        else:

            health = "🟢 HEALTHY"

        answer = (
            f"🏭 Warehouse Health: {health}\n\n"
            f"Products analyzed: {len(inventory_risk)}\n"
            f"Critical risks: {len(critical)}\n"
            f"High risks: {len(high)}\n"
            f"Medium risks: {len(medium)}\n"
            f"Low risks: {len(low)}\n"
        )

        if inventory_risk:

            top = inventory_risk[0]

            answer += (
                "\nTop issue:\n"
                f"• {top['product']} — "
                f"{top['score']}/100 "
                f"({top['priority']})"
            )

        return answer


    # ======================================
    # BIGGEST POTENTIAL LOSS
    # ======================================

    if (
        "biggest loss" in question
        or "largest loss" in question
        or "biggest financial risk" in question
        or "most money" in question
        or "largest financial" in question
        or "biggest potential" in question
    ):

        if not inventory_risk:

            return (
                "There is currently no significant "
                "financial inventory risk."
            )

        financial_items = sorted(
            inventory_risk,
            key=lambda item: item["stock_value"],
            reverse=True
        )

        top = financial_items[0]

        answer = (
            "💰 Biggest Potential Inventory Loss\n\n"
            f"{top['product']} has the highest "
            f"exposed inventory value.\n\n"
            f"Inventory value: "
            f"₹{top['stock_value']:,.2f}\n"
            f"Risk score: {top['score']}/100\n"
            f"Priority: {top['priority']}\n"
        )

        if top["reasons"]:

            answer += "\nRisk factors:\n"

            for reason in top["reasons"][:3]:

                answer += f"• {reason}\n"

        answer += (
            "\nRecommended action:\n"
            f"{top['action']}"
        )

        return answer


    # ======================================
    # WHY IS PRODUCT RISKY?
    # ======================================

    if (
        "why is" in question
        or "why is it risky" in question
        or "why risky" in question
        or "why risk" in question
    ):

        matched_item = None

        for item in inventory_risk:

            product_name = (
                item["product"] or ""
            ).lower()

            sku = (
                item["sku"] or ""
            ).lower()

            if (
                product_name in question
                or sku in question
            ):

                matched_item = item
                break

        if matched_item:
            context["last_product"] = matched_item

        if not matched_item:

            return (
                "Tell me the product name or SKU "
                "you want me to analyze.\n\n"
                "For example:\n"
                "• Why is Cake risky?\n"
                "• Why is SKU CAKE001 high risk?"
            )

        answer = (
            f"🔎 {matched_item['product']} "
            f"Risk Analysis\n\n"
            f"Risk score: "
            f"{matched_item['score']}/100\n"
            f"Priority: "
            f"{matched_item['priority']}\n"
            f"Quantity: "
            f"{matched_item['quantity']} units\n"
        )

        if matched_item["days_remaining"] is not None:

            days = matched_item["days_remaining"]

            if days < 0:

                expiry_status = (
                    f"Expired {abs(days)} days ago"
                )

            elif days == 0:

                expiry_status = "Expires today"

            else:

                expiry_status = (
                    f"Expires in {days} days"
                )

            answer += (
                f"Expiry: {expiry_status}\n"
            )

        if matched_item["reasons"]:

            answer += "\nWhy it is risky:\n"

            for reason in matched_item["reasons"]:

                answer += f"• {reason}\n"

        answer += (
            "\nRecommended action:\n"
            f"{matched_item['action']}"
        )

        return answer

    # ======================================
    # OVERALL WAREHOUSE SUMMARY
    # ======================================

    if (
        "biggest problems" in question
        or "main problems" in question
        or "problems today" in question
        or "quick summary" in question
        or "warehouse summary" in question
        or "summarize warehouse" in question
        or "summary of warehouse" in question
    ):

        if not inventory_risk:

            return (
                "🟢 Warehouse Summary\n\n"
                "Your current inventory looks healthy. "
                "No significant risks were detected."
            )

        critical = [
            item for item in inventory_risk
            if item["priority"] == "CRITICAL"
        ]

        high = [
            item for item in inventory_risk
            if item["priority"] == "HIGH"
        ]

        expiring = [
            item for item in inventory_risk
            if (
                item["days_remaining"] is not None
                and item["days_remaining"] <= 30
            )
        ]

        total_risk_value = sum(
            item["stock_value"]
            for item in inventory_risk
            if item["score"] >= 40
        )

        if critical:

            status = "🔴 Critical attention required"

        elif high:

            status = "🟠 Warehouse needs attention"

        else:

            status = "🟢 Warehouse is relatively healthy"

        answer = (
            f"🏭 {status}\n\n"
            f"Products analyzed: {len(inventory_risk)}\n"
            f"Critical risks: {len(critical)}\n"
            f"High risks: {len(high)}\n"
            f"Expiry risks within 30 days: {len(expiring)}\n"
            f"Potentially exposed inventory value: "
            f"₹{total_risk_value:,.2f}\n"
        )

        answer += "\nTop issues:\n"

        for item in inventory_risk[:3]:

            answer += (
                f"• {item['product']} — "
                f"{item['score']}/100 "
                f"({item['priority']})\n"
            )

        answer += (
            "\nRecommended focus:\n"
            f"{inventory_risk[0]['action']}"
        )

        return answer


    # ======================================
    # COMBINED RISK + VALUE QUESTION
    # ======================================

    if (
        (
            "risk" in question
            and "value" in question
        )
        or (
            "attention" in question
            and "money" in question
        )
        or "financial impact" in question
    ):

        if not inventory_risk:

            return (
                "There are currently no significant "
                "inventory risks."
            )

        high_value_items = sorted(
            inventory_risk,
            key=lambda item: item["stock_value"],
            reverse=True
        )[:3]

        answer = (
            "💰 Risk & Financial Impact\n\n"
            "These products combine significant "
            "inventory risk with inventory value:\n\n"
        )

        for item in high_value_items:

            answer += (
                f"• {item['product']}\n"
                f"  Risk: {item['score']}/100 "
                f"({item['priority']})\n"
                f"  Value: ₹{item['stock_value']:,.2f}\n"
                f"  Action: {item['action']}\n\n"
            )

        return answer


    # ======================================
    # GENERAL ATTENTION QUESTION
    # ======================================

    if (
        "needs attention" in question
        or "need attention" in question
        or "need to worry" in question
        or "should i worry" in question
        or "what should i focus" in question
        or "what should i focus on" in question
    ):

        if not inventory_risk:

            return (
                "🟢 Nothing currently requires "
                "immediate attention."
            )

        answer = (
            "⚠️ Items requiring your attention:\n\n"
        )

        for item in inventory_risk[:5]:

            answer += (
                f"• {item['product']} — "
                f"{item['score']}/100 "
                f"({item['priority']})\n"
                f"  {item['action']}\n\n"
            )

        return answer

    # ======================================
    # DEFAULT RESPONSE
    # ======================================

    return (
        "I can help analyze your current warehouse "
        "inventory, risk scores, expiry status, "
        "low stock, inventory value at risk, "
        "and recommended actions.\n\n"
        "Try asking:\n"
        "• What should I handle first?\n"
        "• Which product has the highest risk?\n"
        "• What products are expiring?\n"
        "• How much inventory value is at risk?\n"
        "• Which products have low stock?\n"
        "• What can WareFlow AI do?"
    )