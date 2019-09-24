import React, { Fragment, Component } from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext } from '../../utils/constants';
import EmptyTip from '../../components/empty-tip';
import Loading from '../../components/loading';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import toaster from '../../components/toast';

class Content extends Component {

  constructor(props) {
    super(props);
  }

  render() {
    const { loading, errorMsg, items } = this.props;
    if (loading) {
      return <Loading />;
    } else if (errorMsg) {
      return <p className="error text-center">{errorMsg}</p>;
    } else {
      const emptyTip = (
        <EmptyTip>
          <h2>{gettext('没有外链审核信息')}</h2>
        </EmptyTip>
      );
      const table = (
        <Fragment>
          <table className="table-hover">
            <thead>
              <tr>
                <th width="33%">{'文件名字'}</th>
                <th width="33%">{'接收对象'}</th>
                <th width="34%">{'创建时间'}</th>
                {/* <th width="10%">{'链接过期时间'}</th>
                <th width="22%">{'下载链接'}</th>
                <th width="10%">{'审核状态'}</th>
                <th width="10%">{'发送人信息'}</th>
                <th width="13%">{'链接下载信息'}</th> */}
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                return (<Item
                  key={index}
                  item={item}
                />);
              })}
            </tbody>
          </table>
        </Fragment>
      );
      return items.length ? table : emptyTip; 
    }
  }
}

class Item extends Component {

  constructor(props) {
    super(props);
    this.state = {
      isOpIconShown: false,
    };
  }

  handleMouseEnter = () => {
    this.setState({isOpIconShown: true});
  }

  handleMouseLeave = () => {
    this.setState({isOpIconShown: false});
  }

  render() {
    let { item } = this.props;

    return (
      <Fragment>
        <tr onMouseEnter={this.handleMouseEnter} onMouseLeave={this.handleMouseLeave}>
          <td>{item.downloads}</td>
          <td>{item.qwe}</td>
          <td>{item.url}</td>
          {/* <td>{item.share_link_url}</td>
          <td><a onClick={this.togglePinganApproveStatusDialog} href="#">{'查看审核信息'}</a></td>
          <td><a onClick={this.togglePinganFromUserDialog} href="#">{'查看发送人'}</a></td>
          <td><a onClick={this.togglePinganFromUserDialog} href="#">{'查看链接下载信息'}</a></td> */}
        </tr>
      </Fragment>
    );
  }
}

const propTypes = {
  toggle: PropTypes.func.isRequired,
};

const fake_item = {
  'downloads': 123,
  'qwe': 'ewq',
  'url': 'https://www.google.com',
}

const fake_List = [
  fake_item, fake_item, fake_item, fake_item
]

class PinganLinkDownloadInfoDialog extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      errorMsg: '',
      loading: false,
      infoList: [],
    };
  }

  componentDidMount() {
    // this.listPinganShareLinkDownloadInfo().then(res => {
    //   this.setState({infoList: res.data.data});
    // }).catch(error => {
    //   let errMessage = Utils.getErrorMsg(error);
    //   toaster.danger(errMessage);
    // });
    this.setState({infoList: fake_List});
  }

  listPinganShareLinkDownloadInfo = (start, end) => {
    let url = seafileAPI.server + '/api/v2.1/admin/logs/share-link-file-audit/';
    return seafileAPI.req.get(url);
  }

  render() {
    let { errorMsg, loading } = this.state;
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('链接下载信息')}</ModalHeader>
        <ModalBody>
          <Content
            loading={loading}
            errorMsg={errorMsg}
            items={this.state.infoList}
          />
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganLinkDownloadInfoDialog.propTypes = propTypes;

export default PinganLinkDownloadInfoDialog;
