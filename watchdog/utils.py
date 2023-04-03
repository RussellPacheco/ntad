def write_to_json(event):
    print("Writing to file")

    with open("file_event.log", "a") as file:
        file.write(f"{event.event_type}    {event.src_path}    {event.dest_path if hasattr(event, 'dest_path') else ''}\n")