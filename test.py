
from phase1 import Phase1
from phase2 import Phase2
from phase3 import Phase3


def main():
    
    user_stories = [
        "Create a report of all customer transactions.",
        "a report of all customer transactions.",
        "As a developer, I want to see the performance metrics for a specific microservice.",
        "As a customer, I can login to the system.",
        "As an admin, I want to approve a new user's request to join.",
        "As a manager, I can grant permissions to another team member.",
        "As a customer, I can place an order.",
        "As a buyer, I can add items to cart.",
        "As a user, I can view order history.",
        "User accounts should be locked after five failed login attempts.",
        "As a user, I want to sign up for a new account.",
        'The system should send an email notification to the user after they have successfully registered.'
    ]
    

    phase1 = Phase1()
    phase1_results = phase1.process_text(user_stories)
    phase1.export_json("phase1.json")

    phase2 = Phase2()
    phase2_results = phase2.analyze_concepts(phase1_results)
    phase2.export_json("phase2.json")
    
    phase3 = Phase3()
    phase3_results = phase3.process_wordnet(phase2_results)
    phase3.export_json("phase3.json")


#     create_final_json(phase1_results, phase2_results, phase3_results, user_stories)

# def create_final_json(phase1_data, phase2_data, phase3_data, original_stories):
   
#     final_data = {
#         "pipeline": "Simple 3-Phase Algorithm",
#         "input": {
#             "user_stories": original_stories,
#             "total_stories": len(original_stories)
#         },
#         "phase1_text_processing": {
#             "extracted_concepts": len(phase1_data["concepts"]),
#             "roles": phase1_data["roles"],
#             "actions": phase1_data["actions"],
#             "objects": phase1_data["objects"]
#         },
#         "phase2_concept_analysis": {
#             "object_frequency": phase2_data["object_frequency"],
#             "total_phase2_records": len(phase2_data["final_output"]),
#             "final_output": len(phase2_data["final_output"])
#         },
#         "phase3_final_output": phase3_data
#     }
    
#     try:
#         with open("FINAL_output.json", 'w', encoding='utf-8') as f:
#             json.dump(final_data, f, indent=2, ensure_ascii=False)
#     except Exception as e:

if __name__ == "__main__":
    main()
