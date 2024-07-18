import typer
import subprocess
import sys
import rdflib
import importlib_resources
import logging

# logging level is INFO
logging.getLogger().setLevel(logging.INFO)
# get root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

app = typer.Typer()


@app.command()
def recompile():
    from brick_haystack_harmonization.bh_to_xeto import BHtoXetoConverter
    from brick_haystack_harmonization.xeto_to_shacl import XetoToShacl
    # first, generate the Xeto library
    input_file = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("brick-haystack.csv"))
    xeto_file = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("xetolib/bh.xeto"))
    template_file = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("bmotif/templates.yml"))
    BHtoXetoConverter().run(input_file, xeto_file, template_file)

    # invoke xeto to create the resolved JSON file
    # rm -rf brick_haystack_harmonization/data/xeto/lib/data/xetolib
    subprocess.run(["rm", "-rf", "xeto/lib/data/xetolib"], check=True)
	# cp -r data/xetolib xeto/lib/data/
    xetolib_path = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("xetolib"))
    subprocess.run(["cp", "-r", xetolib_path, "xeto/lib/data/"], check=True)
    # xeto/bin/xeto json-ast -out data/resolved-bh.json xetolib ashrae.g36
    resolved_bh_file = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("resolved-bh.json"))
    subprocess.run(["xeto/bin/xeto", "json-ast", "-out", resolved_bh_file, "xetolib", "ashrae.g36"], check=True)

    # then, generate the SHACL shapes from the xeto library
    input_file = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("resolved-bh.json"))
    output_file = str(importlib_resources.files("brick_haystack_harmonization.data").joinpath("bh.ttl"))
    XetoToShacl().run(input_file, output_file)


@app.command()
def haystack2brick(haystack_json_file: str, output_graph_file: str):
    from brick_haystack_harmonization.ph2ttl2 import HaystackToRDFTransformer
    processor = HaystackToRDFTransformer()
    model, valid, report = processor.run(haystack_json_file)
    model.serialize(output_graph_file, format=rdflib.util.guess_format(output_graph_file) or "ttl")
    if not valid:
        print(report)
        sys.exit(1)

@app.command()
def hello(name: str):
    typer.echo(f"Hello {name}")

if __name__ == "__main__":
    app()

