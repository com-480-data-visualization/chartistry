# Project of Data Visualization (COM-480)

## Milestone 1 (20th March, 5pm)

### Dataset
**Trending YouTube Video Statistics**

YouTube is the world's largest video-sharing platform, with over two billion logged-in users visiting monthly and roughly 500 hours of video uploaded every minute. Determining what captures collective attention at any given moment is a question of cultural, economic, and behavioral interest. YouTube itself maintains a curated "Trending" tab, updated continuously, which surfaces videos gaining the most traction across the platform. According to Variety, trending rankings are determined not just by view counts, but by a mix of interactions — including shares, comments, and likes — designed to reflect current momentum rather than overall accumulation. It is this list, and its daily evolution, that the ["Trending YouTube Video Statistics"](https://www.kaggle.com/datasets/datasnaek/youtube-new/data) dataset captures.

Available on Kaggle, the dataset contains daily snapshots of up to 200 top trending videos across eleven regions including the US, UK, Germany, France, Canada, and Japan, spanning from 2006 to 2018. Each region is stored as a separate CSV file, making the dataset modular and straightforward to work with at the level of individual countries or in cross-regional comparisons. Each record contains 16 columns: video and channel identifiers, publish and trending dates, engagement metrics (views, likes, dislikes, comment count), tags, and status flags. Video categories are stored separately in a companion JSON file per region, requiring a simple join to decode numeric category IDs into readable labels.

Data quality is strong overall. The main preprocessing steps involve converting dates to a proper datetime format, removing duplicate records, handling encoding issues in several regional files, filling missing descriptions with a placeholder, and joining the companion category JSON files to decode category identifiers into readable labels. The multi-region structure is the dataset's greatest asset, enabling direct cultural comparisons in content preferences and engagement patterns. Its modest file sizes, clean schema, and low preprocessing overhead make it an ideal candidate for visualization, allowing focus to remain on uncovering what drives virality across different audiences and over time.

### Problematic

This project focuses on the visualization of YouTube trending videos in order to reveal how virality manifests across different contexts. Our goal is to make visible the patterns and differences in how content reaches the trending page.

Through interactive data visualization, we aim to show how virality varies along four main dimensions:
- **Content** (category, tags, title, thumbnail)
- **Engagement** (views, likes, comments)
- **Geography** (differences between countries)
- **Time** (evolution between 2006 and 2018)

By combining these perspectives, the project will allow users to explore how trending content differs across regions and how these dynamics have evolved over time.

The visualizations will be designed to encourage exploration and comparison. Users will be able to identify trends such as differences in content preferences between regions or shifts in engagement over the years, helping them intuitively understand how online attention is distributed across geographies, categories, and time periods.

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
#### What others have already done with the data?
The dataset is widely explored in the data science community, with most existing work focusing on descriptive performance metrics. Common analyses include studying engagement ratios — such as the correlation between likes, dislikes, and comment count — to determine which metric best predicts view counts. Others have examined temporal patterns to identify optimal publishing windows, and compared the growth velocity of different content categories (e.g., Entertainment vs. News).

#### Why is our approach original
While prior work treats the metadata as a static performance report, our approach uses it as a scaffold for deeper feature enrichment. We plan to move beyond the raw CSV columns to uncover less obvious drivers of virality across four directions:

* **Rhetorical Hook Taxonomy:** Rather than relying solely on the provided category labels, we plan to use LLMs to classify the linguistic strategy of video titles — for example, distinguishing "Negativity Bias" hooks like _"The worst mistake..."_ from "Knowledge Gap" hooks like _"What they don't tell you..."_
* **Visual Aesthetic Quantification:** By processing thumbnail images, we aim to extract color and composition metrics to test whether "visual loudness" (e.g., high saturation vs. minimalist design) is a cross-cultural prerequisite for trending.
* **The Contagion Map:** Rather than treating the eleven regions in isolation, we plan to track the "viral lag time" — measuring how long it takes for a specific video to jump from one region's trending tab to another's.
* **Creator Sandbox:** Our visualization will include an interactive simulation allowing users to test their own titles and thumbnails against the enriched dataset, exploring where they fall in the global landscape of virality.

These features are planned as part of the final deliverable and represent the core of what distinguishes our project from prior exploratory work on this dataset.

#### What source of inspiration do we take?
We take inspiration from several visual essay-style websites such as ["The Pudding"](https://pudding.cool/) or [“Information is Beautiful”](https://informationisbeautiful.net/), which blends rigorous data processing with playful, interactive exploration.

