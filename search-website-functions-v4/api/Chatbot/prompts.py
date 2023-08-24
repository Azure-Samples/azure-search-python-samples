SYSTEM_MESSAGE = """"You have access to letters from and to 'Coordinador Electrico Nacional' (CEN) which is the entity responsible for coordinating the operation of the interconnected power system in Chile."""

DECOMPOSE_INSTRUCTIONS = """You are now going to decompose the user's [QUERY] into the followging components: Question or information to find, and filters. Keep it short and as close as possible to the original [QUERY]. Fix grammar and spelling mistakes if needed."""

EXAMPLES_DECOMPOSE = """[QUERY]\nComo se obtienen los caudales afluentes utilizados en la programación del Sistema Eléctrico Nacional del 17 de agosto de 2023?\n\n[ANSWER]Query: Como se obtienen los caudales afluentes utilizados en la programación del Sistema Eléctrico Nacional?\nFilters: 17 de agosto de 2023"""

FINAL_ANSWER_INSTRUCTIONS = """You are now going to create the final answer to the user's [QUERY] by using the information found by the system. Create a highly detailed and accurate answer to solve the [QUERY]. You can use Markdown format. Be clear and concise. Use the same language as the user."""