def run_script(**kwargs):
    print("Hello Dr. Stade!")
    return {"result": "done", "workflow_instructions": {"instruction1": "do-this-next-please"}}


if __name__ == '__main__':
    run_script()
