CLI_CHANNEL_NAME = "groce-cli"
GROCE_CHANNEL_NAME = "grocery-list"
LOG_CHANNEL_NAME = "groce-log"
AISLES: dict[str, str] = {
    "Produce": "Fresh fruits and vegetables",
    "Bread/Bakery": "Baked goods and bread",
    "Meat": "Fresh meats and poultry",
    "Pasta": "Dried pasta, sauce, tomato paste, etc.",
    "Hispanic": "Tortillas, Salsas, beans, etc.",
    "International": "Foods from various non hispanic 'international' (from USA POV) cuisines including Asian, Indian, Middle Eastern, and more. Includes rice, sauces, etc",
    "Cereal": "Breakfast cereals and granola",
    "Dairy": "Milk, cheese, yogurt, and eggs",
    "Gluten-Free": "Gluten-free products and alternatives",
    "Beverages": "Drinks and beverages",
    "Canned Goods": "Canned fruits, vegetables, and soups",
    "Frozen Foods": "Frozen meals, vegetables, and desserts",
    "Alcohol": "Beer, wine, and spirits",
    "Pet Supplies": "Pet food and supplies",
    "Household": "Paper goods, cleaning supplies, and toiletries",
    "Misc": "Items that don't fit into other categories",
}
ALLOWED_AISLES = list(AISLES.keys())
