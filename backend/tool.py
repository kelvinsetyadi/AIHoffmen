from agno.tools import tool

# Custom Agno Tool
@tool(
    name="SurveyorTool",
    description="Calculates the sum of num_floors, num_gardens, and num_toilets to determine total workers.",
    show_result=True,
    requires_confirmation=False, # Set to False for automatic execution in this context
    cache_results=False,
)
def get_total_workers(num_floors: int, num_gardens: int, num_toilets: int) -> int:
    """
    Calculates the total number of workers by summing the number of floors, gardens, and toilets.
    """
    return num_floors + num_gardens + num_toilets