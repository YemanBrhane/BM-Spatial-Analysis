import numpy as np
from sklearn.metrics.pairwise import euclidean_distances
import seaborn as sns
import matplotlib.pyplot as plt


def remove_overlapping_detection(df, distance_threshold, batch_size=8000, batch_overlap=400):

    """
    Note: this code removes overlapping prediction and return the corrected dataframe
    
    Why batch_size?
    
    pairwise distance for large value of 'n' needs large memory and it need to be divided into batches
    threshold = 5000, empirically chosen.
    first csv data is sorted by X and Y and divided into batches. if there are overlapping detection,
    they are likely to be with in a given batch
    
    Why batch_overlap?
    when batches are extracted without overlap, over-detection cells can be on different batches and
    will not be identified. Thus, overlap between batches is needed.
    """
    print('     * remove over detection.')

    assert all([a in df.columns for a in ['X', 'Y']]), 'input dataframe should have X, and Y coordinates.' \
                                                       'df[columns]={}'.format(df.columns)
    if 'Probability' not in df.columns:
        df['Probability'] = [1.0]*len(df)

    df['tp'] = ['Yes'] * len(df)  # initialize every cell as true positive prediction
    num_cells = len(df)  # number of cells
    
    df = df.sort_values(by=['X', 'Y']).reset_index(drop=True)
    
    if num_cells > batch_size:
        num_batches = int(np.ceil(num_cells / batch_size))
        for i in range(num_batches):

            if i != num_batches - 1:
                if i == 0:
                    start = i * batch_size
                else:
                    start = i * batch_size - batch_overlap
                    
                end = start + batch_size
                batch_df = df.loc[start: end, :].reset_index(drop=True)
                fn_index = get_false_positive_cells_index(batch_df.copy(), distance_threshold)
            else:
                start = i * batch_size - batch_overlap
                batch_df = df.loc[start:, :].reset_index(drop=True)
                fn_index = get_false_positive_cells_index(batch_df.copy(), distance_threshold)
            
            # update tp column
            fn_index = start + fn_index
            df.loc[fn_index, 'tp'] = 'No'
            
    else:
        fn_index = get_false_positive_cells_index(df.copy(), distance_threshold)
        df.loc[fn_index, 'tp'] = 'No'

    df = df.loc[df['tp'] == 'Yes', :].reset_index(drop=True)
    df = df.drop(columns=['tp'])

    # return corrected predictions
    return df


def get_false_positive_cells_index(df, distance_threshold):
    # tp = df['tp'].to_numpy()
    dist = euclidean_distances(df[['X', 'Y']].to_numpy(), df[['X', 'Y']].to_numpy())
    
    # to remove diagonal fill them with a large value, 1000 chosen here
    np.fill_diagonal(dist, 1000.0)
    # print(dist)
    dst_thresh = (dist < distance_threshold) * 1
    # print(dist)
    row, _ = np.where(dist < distance_threshold)

    del dist
    nn_row = list(np.unique(row))
    
    # for every cell with a nearby cell (less than distance threshold), compare values based on cell prediction area and
    #  cell prediction probability, select the most likely cell from the cell under consideration and neighbouring cells
    area_pro = np.multiply(df['Probability'].to_numpy(), df['Area'].to_numpy())
    area_pro = np.repeat(np.reshape(area_pro, (1, len(area_pro))), repeats=len(df), axis=0)
    
    # mask out non neighbouring cells,
    # update distance threshold matrix to include diagonal
    np.fill_diagonal(dst_thresh, 1.0)
    area_pro_dist = np.multiply(area_pro, dst_thresh)

    del dst_thresh, area_pro

    for r in nn_row:
        
        if df.loc[r, 'tp'] == 'Yes':
            arg_max = np.argmax(area_pro_dist[r, :])  # index of the true cell
            cols = np.where(area_pro_dist[r, :])[0]
            
            # del nn_cols[arg_max]
            # tp[nn_cols] = 'No'
            for col_index in list(cols):
                if col_index != arg_max:
                    df.loc[col_index, 'tp'] = 'No'
    
    # get index false positive cells
    fn_indices = np.where(df['tp'] == 'No')[0]
    
    return fn_indices


def mark_cell_center(im, df, file_name, cell_2_color_dict=None, color='#00ff00'):
    plt.close('all')
    
    dpi = 100
    height, width, nbands = im.shape

    # What size does the figure need to be in inches to fit the image?
    fig_size = width / float(dpi), height / float(dpi)

    # Create a figure of the right size with one axes that takes up the full figure
    fig = plt.figure(figsize=fig_size)
    ax = fig.add_axes([0, 0, 1, 1])

    # Hide spines, ticks, etc.
    ax.axis('off')

    # Display the image.
    ax.imshow(im, interpolation='nearest')

    # display cells on the image
    if cell_2_color_dict is not None:
        # if there are images without cells input df can be without column, 'Class'
        # this line adds Class column
        if 'Class' not in df.columns.to_list():
            df['Class'] = 'CellA'
        sns.scatterplot(x='X',
                        y='Y',
                        data=df,
                        hue='Class',
                        ax=ax,
                        edgecolor=None,
                        s=6,
                        palette=cell_2_color_dict,
                        legend=False)
    else:

        if 'Class' not in df.columns.to_list():
            df['Class'] = 'CellA'
        sns.scatterplot(x='X',
                        y='Y',
                        data=df,
                        ax=ax,
                        edgecolor=None,
                        palette=[color],
                        legend=False,
                        s=1)

    # Ensure we're displaying with square pixels and the right extent.
    # This is optional if you haven't called `plot` or anything else that might
    # change the limits/aspect.  We don't need this step in this case.
    ax.set(xlim=[0, width], ylim=[height, 0], aspect=1)

    # save image with cell annotation
    fig.savefig(file_name, dpi=dpi, transparent=True)
    
    # close figure; if not used there will be memory issue as all figures will be collected
    # as the program run
    plt.close(fig)
