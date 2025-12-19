def plot_nutritional_info(nutritional_info):
    """Function to plot a donut chart with nutritional information and list ingredient weights."""

    # Initialize variables to sum up the total nutritional values
    total_proteins = 0
    total_fats = 0
    total_carbohydrates = 0
    total_calories = 0

    # List to store ingredient details for display
    ingredient_details = []

    # Process the nutritional data for each ingredient
    for ingredient in nutritional_info:
        for name, info in ingredient.items():
            total_proteins += info["proteins"]
            total_fats += info["fats"]
            total_carbohydrates += info["carbohydrates"]
            total_calories += info["calories"]
            # Append ingredient name and weight to the list
            ingredient_details.append(f'{name}: {info["weight"]}g')

    # Prepare data for the donut chart
    labels = "Proteins", "Fats", "Carbohydrates"
    sizes = [total_proteins, total_fats, total_carbohydrates]

    # Create the donut-style pie chart
    fig, ax = plt.subplots()
    fig.patch.set_alpha(0.0)  # Set transparent background

    # Plot pie chart with a 'donut' effect
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda p: f"{p * sum(sizes) / 100:.0f}",
        startangle=90,
        wedgeprops={"width": 0.5},  # Create the 'donut' effect
    )

    # Ensure the pie chart is a perfect circle
    ax.axis("equal")

    # Set text color for labels to white
    for text in texts:
        text.set_color("white")

    # Adjust the position and style of the numbers inside the chart
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(16)
        x, y = autotext.get_position()
        autotext.set_position((x * 1.2, y * 1.2))  # Move numbers closer to the edges

    # Add total calories to the center of the donut chart
    plt.text(
        0,
        0,
        f"{int(total_calories)}\nkcal",
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=20,
        color="white",
    )

    # Render the chart in Streamlit
    st.pyplot(fig, transparent=True)

    # Use Streamlit columns to arrange the ingredient details in two columns
    st.write("### Ingredients and their weight:")

    # Create two columns for displaying the ingredients
    cols = st.columns(2)
    for i, detail in enumerate(ingredient_details):
        col = cols[i % 2]  # Alternate between the two columns
        with col:
            # Create a visually appealing box for each ingredient
            st.markdown(
                f"""
                <div style="background-color:#444; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);">
                    <h4 style="color:white;">{detail}</h4>
                </div>
            """,
                unsafe_allow_html=True,
            )
