import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import KNNImputer
from sklearn.feature_selection import chi2, f_classif
from statsmodels.stats.outliers_influence import variance_inflation_factor
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from typing import Dict, Any, Tuple, List
import os
import warnings
import logging

warnings.filterwarnings('ignore')


class AutoEDAPipeline:
    """Enhanced Automated EDA Pipeline with advanced visualizations"""

    def __init__(self):
        self.charts_dir = "static/charts"
        os.makedirs(self.charts_dir, exist_ok=True)
        self.knn_neighbors = 5
        self.iqr_factor = 1.5

    def run_analysis(self, df: pd.DataFrame, task_type: str, target_col: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        report = {}
        logging.info("🔵 Starting EDA Pipeline...")

        # Normalize column names first for consistency
        df.columns = df.columns.str.strip().str.replace(' ', '_', regex=False)

        # Normalize target column name too
        target_col = target_col.strip().replace(' ', '_')

        # Step 1: Data Quality Assessment
        try:
            report["data_quality"] = self._assess_data_quality(df)
            logging.info("✅ Data quality assessment completed.")
        except Exception as e:
            logging.error(f"❌ Data quality assessment failed: {e}")
            report["data_quality"] = {}

        # Step 2: Clean column names and remove unnecessary columns
        try:
            cleaned_df = self._clean_data(df, target_col)
            report["cleaned_shape"] = cleaned_df.shape
            logging.info("✅ Data cleaning completed.")
        except Exception as e:
            logging.error(f"❌ Data cleaning failed: {e}")
            raise

        # Step 3: Feature Engineering
        try:
            engineered_df = self._engineer_features(cleaned_df, target_col, task_type)
            logging.info("✅ Feature engineering completed.")
        except Exception as e:
            logging.error(f"❌ Feature engineering failed: {e}")
            raise

        # Step 4: Statistical Analysis
        try:
            report["statistics"] = self._statistical_analysis(engineered_df, target_col, task_type)
            logging.info("✅ Statistical analysis completed.")
        except Exception as e:
            logging.error(f"❌ Statistical analysis failed: {e}")
            report["statistics"] = {}

        # Step 5: Feature Importance
        try:
            report["feature_importance"] = self._analyze_feature_importance(engineered_df, target_col, task_type)
            logging.info("✅ Feature importance analysis completed.")
        except Exception as e:
            logging.error(f"❌ Feature importance failed: {e}")
            report["feature_importance"] = {}

        logging.info("🟢 EDA Pipeline successfully completed.")
        return engineered_df, report

    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        logging.info("Assessing data quality...")
        try:
            quality_report = {
                "shape": df.shape,
                "memory_usage": df.memory_usage(deep=True).sum(),
                "dtypes": df.dtypes.value_counts().to_dict(),
                "missing_values": df.isnull().sum().to_dict(),
                "missing_percentage": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
                "duplicate_rows": df.duplicated().sum(),
                "unique_values": {col: df[col].nunique() for col in df.columns},
                "zero_values": (df == 0).sum().to_dict(),
                "negative_values": (df.select_dtypes(include=[np.number]) < 0).sum().to_dict()
            }

            # Identify potential issues
            issues = []
            for col in df.columns:
                if quality_report["missing_percentage"][col] > 50:
                    issues.append(f"High missing values in {col}: {quality_report['missing_percentage'][col]:.1f}%")

                if df[col].dtype == 'object' and df[col].nunique() == len(df):
                    issues.append(f"Potential ID column: {col}")

            quality_report["potential_issues"] = issues

            return quality_report
        except Exception as e:
            logging.error(f"Data quality assessment failed: {e}")
            return {}

    def _clean_data(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Enhanced data cleaning with logging"""

        logging.info("Starting data cleaning...")
        cleaned_df = df.copy()

        # Clean column names
        cleaned_df.columns = cleaned_df.columns.str.strip().str.replace(' ', '_', regex=False)
        logging.info(f"Column names cleaned. Total columns: {len(cleaned_df.columns)}")

        # Remove ID-like columns but never remove target column
        id_cols = [col for col in cleaned_df.columns
                   if any(keyword in col.lower() for keyword in ['id', 'index', 'key']) and col != target_col]
        cleaned_df = cleaned_df.drop(columns=id_cols, errors='ignore')
        logging.info(f"Removed ID-like columns (except target): {id_cols}")

        # Remove high-null columns (>60% missing)
        high_null_cols = cleaned_df.columns[cleaned_df.isnull().mean() > 0.6].tolist()
        cleaned_df = cleaned_df.drop(columns=high_null_cols)
        logging.info(f"Removed high-null columns: {high_null_cols}")

        # Convert string numbers to numeric where possible
        for col in cleaned_df.select_dtypes(include=['object']).columns:
            numeric_series = pd.to_numeric(cleaned_df[col], errors='coerce')
            if numeric_series.notna().mean() > 0.7:
                cleaned_df[col] = numeric_series
                logging.info(f"Converted column '{col}' to numeric")

        logging.info(f"Data cleaning completed. Remaining columns: {len(cleaned_df.columns)}")
        return cleaned_df

    def _engineer_features(self, df: pd.DataFrame, target_col: str, task_type: str) -> pd.DataFrame:
        """Advanced feature engineering with logging and error handling"""

        logging.info("🔵 Starting feature engineering...")

        try:
            if target_col not in df.columns:
                raise ValueError(f"Target column '{target_col}' not found")
            logging.info(f"Target column '{target_col}' found.")

            engineered_df = df.copy()

            # Separate features and target
            y = engineered_df[target_col]
            X = engineered_df.drop(columns=[target_col])
            logging.info("✅ Target separated from features.")

            # Step 1: KNN Imputation
            try:
                X_imputed = self._knn_impute(X)
                logging.info("✅ KNN imputation completed.")
            except Exception as e:
                logging.error(f"❌ KNN imputation failed: {e}")
                raise

            # Step 2: Categorical Encoding
            try:
                X_encoded = self._encode_categorical(X_imputed)
                logging.info("✅ Categorical encoding completed.")
            except Exception as e:
                logging.error(f"❌ Encoding failed: {e}")
                raise

            # Step 3: Scaling
            try:
                X_scaled = self._scale_features(X_encoded)
                logging.info("✅ Feature scaling completed.")
            except Exception as e:
                logging.error(f"❌ Scaling failed: {e}")
                raise

            # Step 4: Target Encoding (classification only)
            if task_type == "classification" and y.dtype == 'object':
                try:
                    y_encoded = LabelEncoder().fit_transform(y)
                    y = pd.Series(y_encoded, index=y.index, name=target_col)
                    logging.info("✅ Target encoding (classification) completed.")
                except Exception as e:
                    logging.error(f"❌ Target encoding failed: {e}")
                    raise

            # Step 5: Outlier Removal
            try:
                X_clean, y_clean = self._remove_outliers(X_scaled, y)
                logging.info("✅ Outlier removal completed.")
            except Exception as e:
                logging.error(f"❌ Outlier removal failed: {e}")
                raise

            final_df = pd.concat([X_clean, y_clean], axis=1)
            logging.info("🟢 Feature engineering fully completed.")
            return final_df.dropna()

        except Exception as e:
            logging.error(f"❌ Full feature engineering failed: {e}")
            raise

    def _knn_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        """KNN imputation for missing values with logging and error handling"""

        logging.info("🔵 Starting KNN imputation...")

        try:
            cat_cols = df.select_dtypes(include=['object']).columns.tolist()
            df_temp = df.copy()

            encoders = {}

            # Step 1: Encoding categorical columns before imputation
            try:
                for col in cat_cols:
                    encoder = LabelEncoder()
                    df_temp[col] = encoder.fit_transform(df_temp[col].astype(str))
                    encoders[col] = encoder
                logging.info(f"✅ Encoded categorical columns for KNN imputation: {cat_cols}")
            except Exception as e:
                logging.error(f"❌ Encoding before KNN imputation failed: {e}")
                raise

            # Step 2: Apply KNN imputation
            try:
                imputer = KNNImputer(n_neighbors=self.knn_neighbors)
                df_imputed = pd.DataFrame(
                    imputer.fit_transform(df_temp),
                    columns=df_temp.columns,
                    index=df_temp.index
                )
                logging.info("✅ KNN imputation completed.")
            except Exception as e:
                logging.error(f"❌ KNN imputation failed: {e}")
                raise

            # Step 3: Decode categorical columns back to original labels
            try:
                for col in cat_cols:
                    df_imputed[col] = df_imputed[col].round().astype(int)
                    df_imputed[col] = encoders[col].inverse_transform(df_imputed[col])
                logging.info(f"✅ Decoded categorical columns back to original labels: {cat_cols}")
            except Exception as e:
                logging.error(f"❌ Decoding categorical columns after KNN failed: {e}")
                raise

            logging.info("🟢 KNN imputation fully completed.")
            return df_imputed

        except Exception as e:
            logging.error(f"❌ Full KNN imputation failed: {e}")
            raise

    def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced categorical encoding with logging and error handling"""

        logging.info("🔵 Starting categorical encoding...")

        try:
            encoded_df = df.copy()

            cat_cols = df.select_dtypes(include=['object']).columns.tolist()
            logging.info(f"Found categorical columns: {cat_cols}")

            for col in cat_cols:
                try:
                    unique_count = df[col].nunique()
                    logging.info(f"Encoding column '{col}' with {unique_count} unique values")

                    if unique_count <= 10:
                        # One-hot encoding for low cardinality
                        dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                        encoded_df = pd.concat([encoded_df.drop(col, axis=1), dummies], axis=1)
                        logging.info(f"✅ One-hot encoded column: {col}")
                    else:
                        # Label encoding for high cardinality
                        encoded_df[col] = LabelEncoder().fit_transform(df[col])
                        logging.info(f"✅ Label encoded column: {col}")

                except Exception as e:
                    logging.error(f"❌ Encoding failed for column '{col}': {e}")
                    raise

            logging.info("🟢 Categorical encoding fully completed.")
            return encoded_df

        except Exception as e:
            logging.error(f"❌ Full categorical encoding failed: {e}")
            raise

    def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Feature scaling with logging and error handling"""

        logging.info("🔵 Starting feature scaling...")

        try:
            scaler = StandardScaler()
            scaled_array = scaler.fit_transform(df)
            scaled_df = pd.DataFrame(scaled_array, columns=df.columns, index=df.index)
            logging.info("🟢 Feature scaling completed successfully.")
            return scaled_df

        except Exception as e:
            logging.error(f"❌ Feature scaling failed: {e}")
            raise

    def _remove_outliers(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """IQR-based outlier removal with logging and error handling"""

        logging.info("🔵 Starting outlier removal...")

        try:
            Q1 = X.quantile(0.25)
            Q3 = X.quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - self.iqr_factor * IQR
            upper_bound = Q3 + self.iqr_factor * IQR

            outlier_mask = ~((X < lower_bound) | (X > upper_bound)).any(axis=1)

            outliers_removed = (~outlier_mask).sum()
            logging.info(f"✅ Outlier removal completed. Total rows removed: {outliers_removed}")

            return X[outlier_mask], y[outlier_mask]

        except Exception as e:
            logging.error(f"❌ Outlier removal failed: {e}")
            return X, y  # fail-safe return original data

    async def _generate_visualizations(self, df: pd.DataFrame, target_col: str, task_type: str) -> Dict[str, str]:
        """Generate comprehensive visualizations with logging and error handling"""

        logging.info("🔵 Starting visualization generation...")
        visualizations = {}

        # Target distribution
        try:
            target_dist_path = await self._plot_target_distribution(df[target_col], task_type)
            visualizations["target_distribution"] = target_dist_path
            logging.info("✅ Target distribution plot generated.")
        except Exception as e:
            logging.error(f"❌ Target distribution plot failed: {e}")

        # Correlation heatmap
        try:
            corr_path = await self._plot_correlation_heatmap(df)
            visualizations["correlation_heatmap"] = corr_path
            logging.info("✅ Correlation heatmap generated.")
        except Exception as e:
            logging.error(f"❌ Correlation heatmap failed: {e}")

        # Feature distributions
        try:
            feat_dist_path = await self._plot_feature_distributions(df, target_col)
            visualizations["feature_distributions"] = feat_dist_path
            logging.info("✅ Feature distributions plot generated.")
        except Exception as e:
            logging.error(f"❌ Feature distributions plot failed: {e}")

        # Pairplot for key features
        try:
            pairplot_path = await self._plot_pairplot(df, target_col, task_type)
            visualizations["pairplot"] = pairplot_path
            logging.info("✅ Pairplot generated.")
        except Exception as e:
            logging.error(f"❌ Pairplot failed: {e}")

        # Box plots for outlier detection
        try:
            boxplot_path = await self._plot_outlier_detection(df, target_col)
            visualizations["outlier_detection"] = boxplot_path
            logging.info("✅ Outlier detection boxplots generated.")
        except Exception as e:
            logging.error(f"❌ Outlier detection plot failed: {e}")

        logging.info("🟢 Visualization generation fully completed.")
        return visualizations

    async def _plot_target_distribution(self, target: pd.Series, task_type: str) -> str:
        """Plot target variable distribution with logging and error handling"""

        logging.info("🔵 Generating target distribution plot...")

        try:
            plt.figure(figsize=(10, 6))

            if task_type == "classification":
                target.value_counts().plot(kind='bar')
                plt.title('Target Variable Distribution (Classification)')
                plt.ylabel('Count')
            else:
                plt.hist(target, bins=30, alpha=0.7, edgecolor='black')
                plt.title('Target Variable Distribution (Regression)')
                plt.ylabel('Frequency')

            plt.xlabel('Target Value')
            plt.tight_layout()

            path = f"{self.charts_dir}/target_distribution.png"
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()

            logging.info(f"✅ Target distribution plot saved at {path}")
            return path

        except Exception as e:
            logging.error(f"❌ Target distribution plot generation failed: {e}")
            return ""

    async def _plot_correlation_heatmap(self, df: pd.DataFrame) -> str:
        """Plot correlation heatmap with logging and error handling"""

        logging.info("🔵 Generating correlation heatmap...")

        try:
            plt.figure(figsize=(12, 10))

            corr_matrix = df.select_dtypes(include=[np.number]).corr()

            sns.heatmap(
                corr_matrix,
                annot=True,
                cmap='coolwarm',
                center=0,
                square=True,
                fmt='.2f'
            )

            plt.title('Feature Correlation Heatmap')
            plt.tight_layout()

            path = f"{self.charts_dir}/correlation_heatmap.png"
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()

            logging.info(f"✅ Correlation heatmap saved at {path}")
            return path

        except Exception as e:
            logging.error(f"❌ Correlation heatmap generation failed: {e}")
            return ""

    async def _plot_feature_distributions(self, df: pd.DataFrame, target_col: str) -> str:
        """Plot feature distributions with logging and error handling"""

        logging.info("🔵 Generating feature distributions...")

        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col != target_col]

            n_features = min(len(numeric_cols), 9)  # Limit to 9 features
            cols = 3
            rows = (n_features + cols - 1) // cols

            plt.figure(figsize=(15, 5 * rows))

            for i, col in enumerate(numeric_cols[:n_features]):
                plt.subplot(rows, cols, i + 1)
                plt.hist(df[col], bins=30, alpha=0.7, edgecolor='black')
                plt.title(f'Distribution of {col}')
                plt.xlabel(col)
                plt.ylabel('Frequency')

            plt.tight_layout()

            path = f"{self.charts_dir}/feature_distributions.png"
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()

            logging.info(f"✅ Feature distributions saved at {path}")
            return path

        except Exception as e:
            logging.error(f"❌ Feature distributions generation failed: {e}")
            return ""

    async def _plot_pairplot(self, df: pd.DataFrame, target_col: str, task_type: str) -> str:
        """Plot pairplot for key features with logging and error handling"""

        logging.info("🔵 Generating pairplot...")

        try:
            numeric_df = df.select_dtypes(include=[np.number])

            if target_col in numeric_df.columns:
                correlations = numeric_df.corr()[target_col].abs().sort_values(ascending=False)
                top_features = correlations.head(6).index.tolist()  # Include target

                subset_df = df[top_features]

                plt.figure(figsize=(12, 10))

                if task_type == "classification":
                    sns.pairplot(subset_df, hue=target_col, diag_kind='hist')
                else:
                    sns.pairplot(subset_df, diag_kind='hist')

                plt.suptitle('Pairplot of Top Correlated Features', y=1.02)

                path = f"{self.charts_dir}/pairplot.png"
                plt.savefig(path, dpi=300, bbox_inches='tight')
                plt.close()

                logging.info(f"✅ Pairplot saved at {path}")
                return path

            else:
                logging.warning("⚠️ Target column not found in numeric features — skipping pairplot.")
                return ""

        except Exception as e:
            logging.error(f"❌ Pairplot generation failed: {e}")
            return ""

    async def _plot_outlier_detection(self, df: pd.DataFrame, target_col: str) -> str:
        """Plot box plots for outlier detection with logging and error handling"""

        logging.info("🔵 Generating outlier detection boxplots...")

        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col != target_col]

            n_features = min(len(numeric_cols), 6)
            cols = 3
            rows = (n_features + cols - 1) // cols

            plt.figure(figsize=(15, 5 * rows))

            for i, col in enumerate(numeric_cols[:n_features]):
                plt.subplot(rows, cols, i + 1)
                plt.boxplot(df[col].dropna())
                plt.title(f'Box Plot - {col}')
                plt.ylabel(col)

            plt.tight_layout()

            path = f"{self.charts_dir}/outlier_detection.png"
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()

            logging.info(f"✅ Outlier detection boxplots saved at {path}")
            return path

        except Exception as e:
            logging.error(f"❌ Outlier detection boxplot generation failed: {e}")
            return ""

    def _statistical_analysis(self, df: pd.DataFrame, target_col: str, task_type: str) -> Dict[str, Any]:
        """Comprehensive statistical analysis with logging and error handling"""

        logging.info("🔵 Starting statistical analysis...")

        try:
            stats = {}

            # Basic statistics
            stats["descriptive"] = df.describe().to_dict()
            logging.info("✅ Descriptive statistics generated.")

            if target_col in df.columns:
                target = df[target_col]

                if task_type == "classification":
                    stats["target"] = {
                        "unique_classes": int(target.nunique()),
                        "class_distribution": target.value_counts().to_dict(),
                        "class_balance": target.value_counts(normalize=True).to_dict()
                    }
                    logging.info("✅ Target analysis (classification) generated.")
                else:
                    stats["target"] = {
                        "mean": float(target.mean()),
                        "median": float(target.median()),
                        "std": float(target.std()),
                        "skewness": float(target.skew()),
                        "kurtosis": float(target.kurtosis())
                    }
                    logging.info("✅ Target analysis (regression) generated.")
            else:
                logging.warning(f"⚠️ Target column '{target_col}' not found in dataset.")

            logging.info("🟢 Statistical analysis fully completed.")
            return stats

        except Exception as e:
            logging.error(f"❌ Statistical analysis failed: {e}")
            return {}

    def _analyze_feature_importance(self, df: pd.DataFrame, target_col: str, task_type: str) -> Dict[str, Any]:
        """Analyze feature importance using statistical tests with logging and error handling"""

        logging.info("🔵 Starting feature importance analysis...")

        try:
            if target_col not in df.columns:
                logging.warning(f"⚠️ Target column '{target_col}' not found for feature importance.")
                return {}

            X = df.drop(columns=[target_col])
            y = df[target_col]

            importance_scores = {}

            if task_type == "classification":
                scores, p_values = chi2(X, y)
                logging.info("✅ Chi-Square test applied for classification task.")
            else:
                scores, p_values = f_classif(X, y)
                logging.info("✅ F-test applied for regression task.")

            for i, col in enumerate(X.columns):
                importance_scores[col] = {
                    "score": float(scores[i]),
                    "p_value": float(p_values[i]),
                    "significant": p_values[i] < 0.05
                }

            logging.info("🟢 Feature importance analysis completed.")
            return importance_scores

        except Exception as e:
            logging.error(f"❌ Feature importance analysis failed: {e}")
            return {}