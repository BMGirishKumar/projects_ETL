import csv
import random

def generate_csv(file_path="massive_dataset.csv", total_rows=1000000):
    print(f"Creating {file_path} with {total_rows} rows...")
    
    headers = ["id", "user_email", "status", "score"]
    statuses = ["active", " pending ", "active", "inactive"] # Includes spaces to test cleanup
    
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(1, total_rows + 1):
            row = [
                i,
                f"User_{i}@Example.com", # Mixed casing to test lowercasing
                random.choice(statuses),
                round(random.uniform(10.0, 100.0), 2)
            ]
            writer.writerow(row)
            
            if i % 250000 == 0:
                print(f" Generated {i} rows...")
                
    print(f"Successfully generated {file_path}!")

if __name__ == "__main__":
    generate_csv()
