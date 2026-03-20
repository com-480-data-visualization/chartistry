# Project of Data Visualization (COM-480)

## Milestone 1 (20th March, 5pm)

**10% of the final grade**

This is a preliminary milestone to let you set up goals for your final project and assess the feasibility of your ideas.
Please, fill the following sections about your project.

*(max. 2000 characters per section)*

### Dataset



### Problematic

This project focuses on the visualization of YouTube trending videos in order to reveal how virality manifests across different contexts. Our goal is to make visible the patterns and differences in how content reaches the trending page.

Through interactive data visualization, we aim to show how virality varies along four main dimensions:
- **Content** (category, tags, title)
- **Engagement** (views, likes, comments)
- **Geography** (differences between countries)
- **Time** (evolution between 2006 and 2018)

By combining these perspectives, the project will allow users to explore how trending content differs across countries and how these dynamics have evolved over time.

The visualizations are designed to encourage exploration and comparison. Users will be able to identify trends such as differences in content preferences between countries or shifts in engagement over the years, helping them intuitively understand how online attention is distributed across regions, categories, and time periods.

The motivation behind this project lies in the growing influence of platforms like YouTube in shaping cultural and informational landscapes. Making these patterns visible provides a clearer understanding of how digital content circulates globally.

The target audience ranges from general users curious about online trends to content creators and data enthusiasts interested in understanding how virality differs across contexts.



### Exploratory Data Analysis

We merged all country datasets into a single dataframe by adding a country identifier. During loading, some datasets (Japan, South Korea, Mexico, and Russia) had encoding issues, which we handled using UTF-8 with error replacement. Since only a small number of rows were affected, we kept them.

We then performed preprocessing: converting dates to a proper datetime format (accounting for the non-standard trending date), removing duplicates, and filling missing descriptions with a placeholder, as this variable is not critical.

We also engineered additional features, including publication hour, day of the week, and days to trending.

Below is a simple exploratory data analysis. For more details, see the `milestone1` notebook.

---

#### Distribution of Views (Log Scale)

![Log Distribution of Views](images/views_log.png)

Views are highly skewed, with a few videos receiving extremely high values. The log transformation makes the distribution more symmetric, confirming a heavy-tailed behavior.

---

#### Distribution of Views by Country (Log Scale)

![Log Views by Country](images/views_log_country.png)

The skewness is consistent across countries, with slight differences in spread, reflecting variations in content popularity.

---

#### Relationship Between Views and Likes

![Likes vs Views](images/likes_views.png)

There is a strong positive relationship between views and likes, showing that more viewed videos generate more engagement.

---

#### Correlation Between Engagement Metrics

![Correlation Matrix](images/correlation.png)

Views, likes, and comment count are strongly correlated, indicating that popular videos generate high interaction across metrics.

---

#### Publication Day

![Videos by Day](images/week_day.png)

Videos are more frequently published on weekdays, with a peak around Thursday and Friday.

---

#### Publication Hour

![Publish Hour Distribution](images/hour_day.png)

Most videos are published in the afternoon and early evening, especially between 14:00 and 18:00.

#### Days to Trending

Most videos reach trending quickly, usually within 0-2 days. The distribution is skewed, with a few extreme values considered outliers.


### Related work

