def run_script(**kwargs):
    print("Hello Dr. Stade!")
    return {"result": "done", "workflow_instructions": {"retry": "false", "exit": True}}


if __name__ == '__main__':
    run_script()
