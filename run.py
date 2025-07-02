from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True recarrega o servidor a cada alteração
    app.run(debug=True)
