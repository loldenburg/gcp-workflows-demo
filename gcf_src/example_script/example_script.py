def run_script(**kwargs):
    print("Hello Dr. Stade!")
    return {"result": "done", "workflow_instructions": {"retry": False, "exit": True}}


if __name__ == '__main__':
    run_script()
