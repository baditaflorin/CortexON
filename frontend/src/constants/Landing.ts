export const EXAMPLES = [
  {
    title: "Gold Price Alert",
    description:
      "Analyze gold prices to recommend optimal buying opportunities.",
    prompt:
      "Check today's gold prices in Mumbai from Goodreturns.in, then write a Python script that analyzes current prices against recent historical trends (7-day average) to recommend if it's a favorable level to buy.",
  },
  {
    title: "Product Analysis",
    description: "Perform product analysis to generate buying recommendations.",
    prompt:
      "Navigate to Flipkart and search for 'wireless headphones'. Scrape the product names and prices of the top 5 results, then write a Python script to calculate their average price. Clearly display each product name, its price, and the computed average price.",
  },
  {
    title: "Regression Model",
    description: "Build a regression model for a public dataset.",
    prompt:
      "Download the Iris dataset, load it into a Python environment, and build a linear regression model to predict petal length based on sepal length. Execute the model and display predicted petal lengths for the following new sepal length inputs: [5.0, 5.5, 6.0, 6.5, 7.0].",
  },
];
