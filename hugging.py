from huggingface_hub import HfApi

api = HfApi()
api.create_repo(repo_id="rajmahahe/TrashNet_Model", repo_type="model", exist_ok=True)
api.upload_file(
    path_or_fileobj="backend/TrashNet_Model.h5",
    path_in_repo="TrashNet_Model.h5",
    repo_id="kasinadhsarma/TrashNet_Model",
    repo_type="model"
)
