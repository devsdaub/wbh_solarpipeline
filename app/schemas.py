import pandera.pandas as pa

HOURLY_WEATHER_SCHEMA = pa.DataFrameSchema(
    {
        "plant_id": pa.Column(int),
        "timestamp": pa.Column("datetime64[ns, UTC]", unique=True),
        "gti": pa.Column(float, pa.Check.ge(0), nullable=True),
        "temperature": pa.Column(float, pa.Check.in_range(-40, 55), nullable=True),
        "cloud_cover": pa.Column("Int64", pa.Check.in_range(0, 100), nullable=True),
        "cloud_cover_low": pa.Column("Int64", pa.Check.in_range(0, 100), nullable=True),
        "cloud_cover_mid": pa.Column("Int64", pa.Check.in_range(0, 100), nullable=True),
        "cloud_cover_high": pa.Column("Int64", pa.Check.in_range(0, 100), nullable=True),
        "visibility": pa.Column(float, nullable=True),
    },
    strict=True,
    coerce=True,
)

HOURLY_AIR_SCHEMA = pa.DataFrameSchema(
    {
        "plant_id": pa.Column(int),
        "timestamp": pa.Column("datetime64[ns, UTC]", unique=True),
        "dust": pa.Column(float, pa.Check.ge(0), nullable=True),
        "pm10": pa.Column(float, pa.Check.ge(0), nullable=True),
    },
    strict=True,
    coerce=True,
)