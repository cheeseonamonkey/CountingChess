import asciichartpy as acp


def plot_vectors(game_vectors):
    for i, vectors in enumerate(game_vectors):
        print(f"\n{'='*60}\nGame {i + 1}\n{'='*60}")
        for metric, values in vectors.items():
            print(f"\n{metric.upper()}:")
            print(acp.plot(values, {'height': 3}))
