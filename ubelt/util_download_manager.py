"""
A simple download manager
"""

__all__ = ['DownloadManager']


class DownloadManager:
    """
    Simple implementation of the download manager

    Example:
        >>> # xdoctest: +REQUIRES(--network)
        >>> import ubelt as ub
        >>> # Download a file with a known hash
        >>> manager = ub.DownloadManager()
        >>> job = manager.submit(
        >>>     'http://i.imgur.com/rqwaDag.png',
        >>>     hash_prefix='31a129618c87dd667103e7154182e3c39a605eefe90f84f2283f3c87efee8e40'
        >>> )
        >>> fpath = job.result()
        >>> print('fpath = {!r}'.format(fpath))

    Example:
        >>> # Does not require network
        >>> import ubelt as ub
        >>> manager = ub.DownloadManager()
        >>> for i in range(100):
        ...     job = manager.submit('localhost/might-not-exist-i-{}'.format(i))
        >>> file_paths = []
        >>> for job in manager.as_completed(prog=True):
        ...     try:
        ...         fpath = job.result()
        ...         file_paths += [fpath]
        ...     except Exception:
        ...         pass
        >>> print('file_paths = {!r}'.format(file_paths))

    Example:
        >>> # xdoctest: +REQUIRES(--network)
        >>> import pytest
        >>> import ubelt as ub
        >>> manager = ub.DownloadManager()
        >>> item1 = {
        >>>     'url': 'https://data.kitware.com/api/v1/item/5b4039308d777f2e6225994c/download',
        >>>     'dst': 'forgot_what_the_name_really_is',
        >>>     'hash_prefix': 'c98a46cb31205cf',
        >>>     'hasher': 'sha512',
        >>> }
        >>> item2 = {
        >>>     'url': 'http://i.imgur.com/rqwaDag.png',
        >>>     'hash_prefix': 'f79ea24571da6ddd2ba12e3d57b515249ecb8a35',
        >>>     'hasher': 'sha1',
        >>> }
        >>> item1 = item2  # hack around SSL error
        >>> manager.submit(**item1)
        >>> manager.submit(**item2)
        >>> for job in manager.as_completed(prog=True, verbose=3):
        >>>     fpath = job.result()
        >>>     print('fpath = {!r}'.format(fpath))

    """
    def __init__(self, download_root=None, mode='thread', max_workers=None,
                 cache=True):
        """
        Args:
            download_root (str | PathLike): default download location
            mode (str): either thread, process, or serial
            cache (bool): defaults to True
            max_workers (int | None): maximum concurrent tasks

        TODO:
            - [ ] Will likely have to initialize and store some sort of
                  "connection state" objects.
        """
        import ubelt as ub
        if download_root is None:
            download_root = ub.ensure_app_config_dir('ubelt', 'dlman')
        self._pool = ub.JobPool(mode=mode, max_workers=max_workers)
        self.download_root = download_root
        self.cache = cache
        if self.cache:
            self._dl_func = ub.grabdata
        else:
            self._dl_func = ub.download

    def submit(self, url, dst=None, hash_prefix=None, hasher='sha256'):
        """
        Add a job to the download Queue

        Args:
            url (str | PathLike): pointer to the data to download
            dst (str | None): The relative or absolute path to download to.
                If unspecified, the destination name is derived from the url.
            hash_prefix (str | None):
               If specified, verifies that the hash of the downloaded file starts with this.
            hasher (str):
                hashing algorithm to use if hash_prefix is specified.
                Defaults to ``'sha256'``.

        Returns:
            concurrent.futures.Future :
                a Future object that will point to the downloaded location.
        """
        job = self._pool.submit(
            self._dl_func, url, fname=dst, dpath=self.download_root,
            hash_prefix=hash_prefix, hasher=hasher, verbose=0,
        )
        return job

    def as_completed(self, prog=None, desc=None, verbose=1):
        """
        Generate completed jobs as they become available

        Args:

            prog (None | bool | type):
                if True, uses a ub.ProgIter progress bar. Can also be a class
                with a compatible progiter API.

            desc (str | None):
                if specified, reports progress with a
                :class:`ubelt.progiter.ProgIter` object.

            verbose (int): verbosity

        Example:
            >>> import pytest
            >>> import ubelt as ub
            >>> download_root = ub.ensure_app_config_dir('ubelt', 'dlman')
            >>> manager = ub.DownloadManager(download_root=download_root,
            >>>                              cache=False)
            >>> for i in range(3):
            >>>     manager.submit('localhost')
            >>> results = list(manager)
            >>> print('results = {!r}'.format(results))
            >>> manager.shutdown()

        """
        if prog is True:
            import ubelt as ub
            prog = ub.ProgIter
        if prog is not None:
            return prog(self._pool.as_completed(), total=len(self), desc=desc,
                        verbose=verbose)
        else:
            return self._pool.as_completed()

    def shutdown(self):
        """
        Cancel all jobs and close all connections.
        """
        self._pool.executor.shutdown()

    def __iter__(self):
        """
        Returns:
            Iterable
        """
        return self.as_completed()

    def __len__(self):
        """
        Returns:
            int
        """
        return len(self._pool)
