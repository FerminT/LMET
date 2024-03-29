import numpy as np
import pandas as pd
from matplotlib import pyplot as plt, colormaps
from numpy import linspace

from scripts.utils import apply_threshold, filter_low_frequency_answers


def plot_distance_to_gt(distances_to_embeddings, sim_threshold, gt_threshold, save_path, error_bars=True):
    fig, ax = plt.subplots(figsize=(10, 6))
    title = f'Distance to ground truth embeddings (lower is better)'
    diff_df, se_df = pd.DataFrame(), pd.DataFrame()
    for model_name in distances_to_embeddings:
        model_distances = distances_to_embeddings[model_name]
        model_distances[['sim']] = apply_threshold(model_distances[['sim']], sim_threshold)
        model_distances[['sim_gt']] = apply_threshold(model_distances[['sim_gt']], gt_threshold)
        model_distances['diff'] = abs(model_distances['sim'] - model_distances['sim_gt'])
        mean_diff = model_distances.groupby('in_stimuli')['diff'].mean()
        std_diff = model_distances.groupby('in_stimuli')['diff'].std()
        se_diff = std_diff / np.sqrt(model_distances.shape[0])
        diff_df = pd.concat([diff_df, mean_diff.to_frame(model_name)], axis=1)
        se_df = pd.concat([se_df, se_diff.to_frame(model_name)], axis=1)
    if error_bars:
        diff_df.plot.bar(xlabel='Words present in stimuli', yerr=se_df, capsize=4, ax=ax)
    else:
        diff_df.plot.bar(xlabel='Words present in stimuli', ax=ax)
    ax.set_title(title)
    ax.legend()
    ax.set_ylabel('Similarity difference with SWOW-RP embeddings')
    plt.savefig(save_path / f'distance_to_gt_t{sim_threshold:.2f}_gt{gt_threshold:.2f}.png')
    plt.show()


def plot_freq_to_sim(basename, similarities_to_answers, save_path, min_appearances):
    fig, ax = plt.subplots(figsize=(15, 6))
    title = f'Human frequency to model similarity ({basename})'
    for model_name in similarities_to_answers:
        model_sim_to_answers = similarities_to_answers[model_name]
        wa_freq_sim_to_plot = filter_low_frequency_answers(model_sim_to_answers, min_appearances)
        ax.scatter(wa_freq_sim_to_plot['similarity'], wa_freq_sim_to_plot['freq'], label=model_name)
    ax.set_xlabel('Model similarity')
    ax.set_ylabel('Human frequency of answer')
    ax.set_title(title)
    ax.legend()
    plt.savefig(save_path / 'freq_to_sim.png')
    plt.show()


def plot_similarity(model_basename, similarities_to_subjs, sim_threshold, save_path, sort_by='texts', error_bars=True):
    if 'baseline' not in similarities_to_subjs:
        print('No baseline model found. Skipping similarity plots')
        return
    for axis, comparable in zip([0, 1], ['subjects', 'cues']):
        fig, ax = plt.subplots(figsize=(25, 15))
        title = f'Avg. similarity to {comparable} answers (baseline: {model_basename}) (higher is better)'
        print(f'\n------{title}------')
        mean_similarities, se_similarities = pd.DataFrame(), pd.DataFrame()
        for model_name in similarities_to_subjs:
            model_sim_to_subjs = apply_threshold(similarities_to_subjs[model_name], sim_threshold)
            mean_subj_sim, se_subj_sim = report_similarity(model_name, model_sim_to_subjs, axis)
            mean_similarities = pd.concat([mean_similarities, mean_subj_sim], axis=1)
            se_similarities = pd.concat([se_similarities, se_subj_sim], axis=1)
        mean_similarities, se_similarities = compare_to_baseline(mean_similarities, se_similarities)
        mean_similarities = mean_similarities.sort_values(by=sort_by, ascending=False)
        se_similarities = se_similarities.reindex(mean_similarities.index)
        if error_bars:
            mean_similarities.plot.bar(yerr=se_similarities, capsize=4, ax=ax)
        else:
            mean_similarities.plot.bar(ax=ax)
        ax.set_title(title, fontsize=15)
        ax.legend(fontsize=15)
        ax.set_ylabel('Similarity diff. to baseline', fontsize=15)
        plt.savefig(save_path / f'{title}.png')
        plt.show()


def plot_loss(loss_sg, loss_fix, model_name, save_path):
    plt.plot(loss_sg, label='W2V', alpha=0.7)
    plt.plot(loss_fix, label='Fix duration', alpha=0.7)
    plt.legend()
    plt.xlabel('Batch')
    plt.ylabel('Loss')
    plt.title(f'{model_name} loss')
    plt.savefig(save_path / 'loss.png')


def compare_to_baseline(mean_similarities, se_similarities):
    baseline_mean, baseline_se = mean_similarities['baseline'], se_similarities['baseline']
    mean_similarities = mean_similarities.drop(columns=['baseline'])
    se_similarities = se_similarities.drop(columns=['baseline'])
    mean_similarities = mean_similarities.subtract(baseline_mean, axis=0)
    se_similarities = se_similarities.add(baseline_se, axis=0)
    return mean_similarities, se_similarities


def report_similarity(model, similarities_df, axis):
    mean_subj_similarity = similarities_df.mean(axis=axis)
    std_subj_similarity = similarities_df.std(axis=axis)
    se_subj_similarity = std_subj_similarity / np.sqrt(similarities_df.shape[1])
    print(f'{model} mean: {mean_subj_similarity.mean():.4f} (std: {std_subj_similarity.mean():.4f})')
    return mean_subj_similarity.to_frame(model), se_subj_similarity.to_frame(model)


def scatterplot_gt_similarities(models_similarities, save_path):
    num_models = len(models_similarities)
    colors = colormaps['viridis'](linspace(0, 1, num_models))
    fig, ax = plt.subplots(num_models, 2, figsize=(15, 6 * num_models), sharex=True, sharey=True)
    for i, model_name in enumerate(models_similarities):
        for j, in_stimuli in enumerate([True, False]):
            title = 'Similarity to in-stimuli words' if in_stimuli else 'Similarity to off-stimuli words'
            model_similarities = models_similarities[model_name]
            model_similarities = model_similarities[model_similarities['in_stimuli'] == in_stimuli]
            ax[i, j].scatter(model_similarities['sim'], model_similarities['sim_gt'], label=model_name,
                             alpha=0.7, color=colors[i])
            ax[i, j].set_title(title)
            ax[i, j].set_xlabel('Model similarity')
            ax[i, j].set_ylabel('Ground truth similarity')
            ax[i, j].legend()
    plt.savefig(save_path / 'scatterplot_similarities.png')
    plt.show()
