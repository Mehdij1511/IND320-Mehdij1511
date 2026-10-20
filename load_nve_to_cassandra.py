from cassandra_data import connect, initialize_schema, insert_reservoir_observation
from nve_data import load_reservoir_data


data = load_reservoir_data()

cluster, session = connect()

try:
    initialize_schema(session)

    for index, row in data.iterrows():
        insert_reservoir_observation(
            session,
            {
                "area_type": row["omrType"],
                "area_number": row["omrnr"],
                "observation_date": row["dato_Id"].date(),
                "year": row["iso_aar"],
                "week": row["iso_uke"],
                "filling_level": row["fyllingsgrad"],
                "capacity_twh": row["kapasitet_TWh"],
                "filled_twh": row["fylling_TWh"],
                "previous_week_filling": row["fyllingsgrad_forrige_uke"],
                "change_filling": row["endring_fyllingsgrad"],
            },
        )

        if (index + 1) % 1000 == 0:
            print(f"Inserted {index + 1} NVE rows")

    print(f"Finished inserting {len(data)} NVE rows")

finally:
    cluster.shutdown()